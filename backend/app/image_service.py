import io
import os
import logging
from PIL import Image, ImageDraw, ImageFilter
from typing import Dict, Any, List, Optional
from app.comfy_client import ComfyClient
from app import face_identity
from app.comfy_workflow_builder import (
    build_flux_workflow,
    build_img2img_refine_workflow,
    build_uso_face_workflow,
)

logger = logging.getLogger(__name__)

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BACKEND_ROOT, "static", "storyboards")
os.makedirs(STATIC_DIR, exist_ok=True)

CHARACTER_REFS_DIR = os.path.join(BACKEND_ROOT, "static", "character_refs")
os.makedirs(CHARACTER_REFS_DIR, exist_ok=True)

# Stage 7: max retries before falling back to the Pillow placeholder, per spec.
MAX_COMFY_RETRIES = 2

# Refinement pass strength. 0.4 rebuilds local detail (hands, fingers, fabric
# folds) while leaving composition and identity intact; higher starts moving
# the frame's content, which would undo the composition pass.
REFINE_DENOISE = 0.4

# Identity pass strength, applied to the WHOLE frame as img2img.
#
# Measured sweep on a profile-face composition (baseline identity 0.500 with no
# identity pass at all):
#     denoise 0.25 -> identity 0.665, composition preserved 0.897
#     denoise 0.40 -> identity 0.722, composition preserved 0.844
#     denoise 0.55 -> identity 0.723, composition preserved 0.799
# Identity plateaus after 0.40 while composition keeps degrading, so 0.40 is
# the knee of the curve -- all of the identity gain, least structural damage.
IDENTITY_DENOISE = 0.40

# FluxGuidance per pass: Flux's 3.5 default everywhere. Lowering it to 2.2 (the
# range Flux "realism" guides recommend for skin texture) was tried on
# 2026-09-30 and rejected: prompt adherence dropped, so each reference angle --
# a separate seed -- drifted into a visibly different person, extras appeared
# in single-character portraits, and the user judged the result far worse than
# the 3.5 references. Identity consistency matters more than skin micro-texture.
COMPOSITION_GUIDANCE = 3.5
DETAIL_GUIDANCE = 3.5   # refinement, identity passes and reference portraits

# Per-face identity pass strength. Much higher than IDENTITY_DENOISE is safe
# here because the repaint is confined to a feathered head mask inside a face
# crop: nothing outside the head can move, so the only thing denoise trades
# against is the face's own expression/angle, not the shot's composition.
# Chosen from a 4-shot sweep (2026-09-30) against the locked references, SFace:
#   0.50 -> RAM 0.563 / SITA 0.738    0.62 -> 0.565 / 0.724    0.75 -> 0.570 / 0.748
# 0.75 had the best average and the best result on the hardest shot, with
# framing and pose intact (the mask confines it to the head).
FACE_IDENTITY_DENOISE = 0.75

class ImageService:
    def __init__(self):
        self.comfy = ComfyClient()

    async def generate_character_portrait(
        self, character_id: str, index: int, prompt: str, seed: int, negative_prompt: str = ""
    ) -> str:
        """
        Stage 6 — generates (or freezes) one character reference image and
        returns its /static path. Uses ComfyUI with the given fixed seed if
        available; otherwise draws a distinct, clearly-labeled placeholder
        portrait so a locked seed is still reproducible without a GPU.

        `negative_prompt` defaults to "" for backward compatibility, but
        callers should pass character_asset_service's
        CHARACTER_PORTRAIT_NEGATIVE_PROMPT -- this path previously always
        sent an empty negative prompt (no anti-illustration, no anti-
        "generic AI face" terms at all), which was a confirmed contributor
        to locked reference portraits coming out both illustrated-looking
        and facially generic/idealized rather than authentic.
        """
        filename = f"{character_id}_{index}.png"
        file_path = os.path.join(CHARACTER_REFS_DIR, filename)

        if await self.comfy.is_healthy():
            logger.info(f"ComfyUI server is healthy. Generating character portrait (seed={seed})...")
            workflow = build_flux_workflow(prompt, negative_prompt, guidance=DETAIL_GUIDANCE)
            for attempt in range(MAX_COMFY_RETRIES):
                img_bytes = await self.comfy.generate_image(workflow, prompt, negative_prompt, seed=seed)
                if img_bytes:
                    with open(file_path, "wb") as f:
                        f.write(img_bytes)
                    return f"/static/character_refs/{filename}"
                logger.warning(f"ComfyUI character portrait attempt {attempt + 1}/{MAX_COMFY_RETRIES} failed.")

        logger.info("ComfyUI not available (or all retries failed). Drawing character portrait placeholder using Pillow...")
        self._draw_character_placeholder(file_path, prompt, seed)
        return f"/static/character_refs/{filename}"


    async def _comfy_generate(self, workflow, prompt: str, negative_prompt: str):
        """One ComfyUI generation with the standard retry count."""
        for attempt in range(MAX_COMFY_RETRIES):
            img_bytes = await self.comfy.generate_image(workflow, prompt, negative_prompt)
            if img_bytes:
                return img_bytes
            logger.warning(f"ComfyUI attempt {attempt + 1}/{MAX_COMFY_RETRIES} returned nothing.")
        return None

    async def _refine_frame(self, img_bytes: bytes, prompt: str, negative_prompt: str, shot_id: str):
        """Pass 1b -- img2img re-denoise of the composed frame.

        Runs on the plain graph with no reference conditioning, so it can
        repair local detail (the malformed hands and fingers that survive a
        first pass) without being able to alter composition.
        """
        uploaded = await self.comfy.upload_image(img_bytes, f"refine_src_{shot_id}.png")
        if not uploaded:
            logger.warning(f"Refinement skipped for shot {shot_id}: init image upload failed.")
            return None
        workflow = build_img2img_refine_workflow(
            prompt, negative_prompt, uploaded, denoise=REFINE_DENOISE, guidance=DETAIL_GUIDANCE
        )
        return await self._comfy_generate(workflow, prompt, negative_prompt)

    async def _apply_identity(
        self, img_bytes: bytes, prompt: str, negative_prompt: str, identities, shot_id: str
    ):
        """Pass 2 -- pull each character's face toward THAT character's references.

        Per face, not per frame. The composed frame's faces are found with
        YuNet, matched to the shot's characters with SFace, and each one is
        cropped, upscaled, repainted from its own character's references inside
        a feathered head mask, then blended back (face_identity). Every present
        character is conditioned -- the old whole-frame pass conditioned one
        focal character, so the other lead in a two-shot drifted -- and the
        mask is what allows FACE_IDENTITY_DENOISE to go far above the 0.40 a
        whole-frame pass can take without breaking composition.

        When no face can be found or matched (back of head, heavy occlusion,
        detector models missing) it falls back to the whole-frame pass on the
        focal character, so identity is never silently skipped.
        """
        usable = [i for i in (identities or []) if i.get("reference_image_paths")]
        if not usable:
            logger.info(f"Shot {shot_id}: no usable reference, skipping identity pass.")
            return None

        frame = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        assignments = []
        if face_identity.is_available():
            faces = face_identity.detect_faces(frame)
            refs = {
                i["name"]: face_identity.reference_features(i.get("local_reference_paths") or [])
                for i in usable
            }
            assignments = face_identity.assign_faces(faces, refs, priority=[i["name"] for i in usable])

        if not assignments:
            logger.info(f"Shot {shot_id}: no matchable face found, using whole-frame identity pass.")
            return await self._apply_identity_whole_frame(img_bytes, prompt, negative_prompt, usable[0], shot_id)

        by_name = {i["name"]: i for i in usable}
        changed = False
        for name, face in assignments:
            identity = by_name[name]
            box = face_identity.crop_box(face, *frame.size)
            crop = face_identity.extract_crop(frame, box)
            mask = face_identity.head_mask(face, box)
            crop_name = await self.comfy.upload_image(face_identity.to_png_bytes(crop), f"face_src_{shot_id}_{name}.png")
            mask_name = await self.comfy.upload_image(face_identity.to_png_bytes(mask.convert("RGB")), f"face_mask_{shot_id}_{name}.png")
            if not crop_name or not mask_name:
                logger.warning(f"Shot {shot_id}: identity pass for {name} skipped, upload failed.")
                continue
            face_prompt = (
                f"Cinematic film still, photorealistic, shot on 35mm film, natural skin texture. "
                f"The face of {name}: {identity.get('description') or ''} Same head angle, expression, "
                "lighting and gaze direction as the input image."
            )
            workflow = build_uso_face_workflow(
                face_prompt, negative_prompt, crop_name, identity["reference_image_paths"],
                width=face_identity.CROP_WORK_SIZE, height=face_identity.CROP_WORK_SIZE,
                denoise=FACE_IDENTITY_DENOISE, mask_filename=mask_name, guidance=DETAIL_GUIDANCE,
            )
            out = await self._comfy_generate(workflow, face_prompt, negative_prompt)
            if not out:
                logger.warning(f"Shot {shot_id}: identity pass produced nothing for {name}.")
                continue
            frame = face_identity.paste_crop(frame, Image.open(io.BytesIO(out)), box, mask)
            changed = True
            logger.info(f"Shot {shot_id}: identity applied to {name}'s face at {box}.")

        return face_identity.to_png_bytes(frame) if changed else None

    async def _apply_identity_whole_frame(
        self, img_bytes: bytes, prompt: str, negative_prompt: str, identity, shot_id: str
    ):
        """Fallback identity pass over the WHOLE frame for one character.

        Low denoise is what keeps it safe: at 0.40 the reference reshapes faces
        while the composition pass's shot size, staging and pose survive
        (measured 0.844 similarity to the pre-pass frame).
        """
        uploaded = await self.comfy.upload_image(img_bytes, f"identity_src_{shot_id}.png")
        if not uploaded:
            logger.warning(f"Shot {shot_id}: identity pass skipped, init upload failed.")
            return None
        workflow = build_uso_face_workflow(
            prompt, negative_prompt, uploaded, identity["reference_image_paths"],
            width=1024, height=640, denoise=IDENTITY_DENOISE, guidance=DETAIL_GUIDANCE,
        )
        out = await self._comfy_generate(workflow, prompt, negative_prompt)
        if out:
            logger.info(f"Shot {shot_id}: whole-frame identity pass applied for {identity.get('name')}.")
        else:
            logger.warning(f"Shot {shot_id}: identity pass produced nothing for {identity.get('name')}.")
        return out

    def _draw_character_placeholder(self, file_path: str, prompt: str, seed: int) -> None:
        """A deterministic (seed-derived color), clearly-labeled placeholder
        portrait — distinct from the shot-card style used for storyboard
        frames, since this represents a character's face/likeness, not a
        composed shot."""
        width, height = 512, 640
        # Seed-derived hue so the same locked seed always renders the same
        # placeholder color, and different characters visibly differ.
        hue = seed % 360
        import colorsys
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, 0.35, 0.85)]

        img = Image.new("RGB", (width, height), color=(r, g, b))
        draw = ImageDraw.Draw(img)
        draw.ellipse([width // 2 - 110, 140, width // 2 + 110, 360], fill=(30, 30, 40))  # head silhouette
        draw.rectangle([width // 2 - 160, 360, width // 2 + 160, height], fill=(30, 30, 40))  # shoulders
        draw.rectangle([0, height - 60, width, height], fill=(0, 0, 0))
        draw.text((16, height - 48), "CHARACTER REFERENCE (placeholder)", fill=(255, 255, 255))
        draw.text((16, height - 28), f"seed={seed}", fill=(200, 200, 200))
        img.save(file_path, "PNG")

    async def _upload_reference_images(self, consistency_params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        USO's reference-conditioned path needs each locked character's
        image sitting in ComfyUI's own input/ folder before a LoadImage
        node can reference it by filename (see comfy_workflow_builder.py's
        module docstring) -- but Stage 6 only ever stores each reference's
        LOCAL /static/character_refs/... URL. Live-tested and confirmed:
        skipping this upload and passing that local URL straight through
        as the LoadImage filename fails ComfyUI's own /prompt validation
        ("Invalid image file: /static/character_refs/...") and silently
        falls back to the Pillow placeholder for every character-locked
        shot. Uploads each reference once per generation call and rewrites
        `identities[].reference_image_paths` to the ComfyUI-side filenames
        upload_image() hands back, on a copy so the caller's dict (which
        may get reused/logged elsewhere) is never mutated.
        """
        if not consistency_params or consistency_params.get("engine") != "USO":
            return consistency_params

        resolved = dict(consistency_params)
        resolved_identities = []
        for identity in consistency_params.get("identities", []):
            uploaded_names = []
            for local_url in identity.get("reference_image_paths", []):
                disk_path = os.path.join(BACKEND_ROOT, local_url.lstrip("/"))
                if not os.path.exists(disk_path):
                    logger.warning(f"Reference image missing on disk, skipping: {disk_path}")
                    continue
                with open(disk_path, "rb") as f:
                    image_bytes = f.read()
                uploaded_name = await self.comfy.upload_image(image_bytes, os.path.basename(disk_path))
                if uploaded_name:
                    uploaded_names.append(uploaded_name)
                else:
                    logger.warning(f"Failed to upload reference image to ComfyUI: {disk_path}")
            resolved_identities.append({
                **identity,
                "reference_image_paths": uploaded_names,
                # Kept so the identity pass can compute SFace features locally.
                "local_reference_paths": identity.get("reference_image_paths", []),
            })
        resolved["identities"] = resolved_identities
        return resolved

    async def generate_storyboard(
        self,
        shot_id: str,
        scene_heading: str,
        shot_info: Dict[str, Any],
        prompt: str,
        negative_prompt: str,
        consistency_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates storyboard image and returns the file path/url.
        Uses ComfyUI (Flux.1-dev, + USO if `consistency_params`
        names locked characters) if available, retrying up to
        MAX_COMFY_RETRIES times before falling back to a Pillow placeholder.
        """
        filename = f"shot_{shot_id}.png"
        file_path = os.path.join(STATIC_DIR, filename)

        # Try ComfyUI first
        if await self.comfy.is_healthy():
            logger.info("ComfyUI server is healthy. Running generation...")
            resolved_params = await self._upload_reference_images(consistency_params)
            identities = (resolved_params or {}).get("identities") or []

            # PASS 1 -- composition, text only. No reference conditioning even
            # when characters are present: a reference concatenated into the
            # frame's own attention field reproduces the reference's structure,
            # which live testing showed overriding shot size (wide shots came
            # back as close-ups), dropping the second character from two-shots,
            # and repeating the same pose regardless of the described action.
            workflow = build_flux_workflow(prompt, negative_prompt, consistency_params=None,
                                           guidance=COMPOSITION_GUIDANCE)
            img_bytes = await self._comfy_generate(workflow, prompt, negative_prompt)

            if img_bytes:
                # PASS 1b -- refinement. Best-effort: keep the composed frame
                # if refinement fails rather than losing a good composition.
                refined = await self._refine_frame(img_bytes, prompt, negative_prompt, shot_id)
                if refined:
                    img_bytes = refined

                # PASS 2 -- identity over the whole frame (see _apply_identity
                # for why this is not done per detected face crop).
                if identities:
                    with_identity = await self._apply_identity(
                        img_bytes, prompt, negative_prompt, identities, shot_id
                    )
                    if with_identity:
                        img_bytes = with_identity

                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                return f"/static/storyboards/{filename}"
                
        # Fallback: Draw a premium cinematic visual concept using Pillow
        logger.info("ComfyUI not available. Generating premium local visual placeholder using Pillow...")
        
        width, height = 1024, 512
        img = Image.new("RGBA", (width, height), color="#000000")
        draw = ImageDraw.Draw(img)
        
        # Background Gradient
        c1 = (10, 10, 18)   # Deep space dark blue
        c2 = (30, 25, 45)   # Indigo/charcoal
        for y in range(height):
            ratio = y / height
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
            
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ol_draw = ImageDraw.Draw(overlay)
        
        # Determine theme color based on prompt
        light_color = (255, 140, 50, 80)
        p_lower = prompt.lower()
        if "sunset" in p_lower or "warm" in p_lower or "golden" in p_lower:
            light_color = (255, 120, 60, 120)
        elif "cold" in p_lower or "blue" in p_lower or "neon" in p_lower:
            light_color = (0, 180, 255, 100)
        elif "forest" in p_lower or "green" in p_lower:
            light_color = (50, 200, 120, 100)
            
        # Draw visual silhouette circles to simulate composition
        ol_draw.ellipse([width//2 - 200, height//2 - 150, width//2 + 200, height//2 + 150], fill=light_color)
        ol_draw.rectangle([0, height - 120, width, height], fill=(15, 12, 22, 255))
        ol_draw.ellipse([width//3 - 60, height//2 - 40, width//3 + 60, height//2 + 80], fill=(5, 5, 8, 255)) # Subject silhouette
        
        # Apply blur to overlay
        blurred_overlay = overlay.filter(ImageFilter.GaussianBlur(35))
        img = Image.alpha_composite(img, blurred_overlay)
        draw = ImageDraw.Draw(img)
        
        # Cinematic letterbox
        letterbox_h = 40
        draw.rectangle([0, 0, width, letterbox_h], fill=(0, 0, 0, 220))
        draw.rectangle([0, height - letterbox_h, width, height], fill=(0, 0, 0, 220))
        
        # Framing safety guide lines
        draw.rectangle([20, 20, width - 20, height - 20], outline=(100, 100, 150, 30), width=1)
        
        # Header Text
        header_text = f"70MM AI STORYBOARD  |  SCENE: {scene_heading.upper()}"
        draw.text((30, 12), header_text, fill=(200, 200, 255, 200))
        
        # Specs Text — `or` (not .get(key, default)) because Stage 4/5-
        # generated shots can have these keys present but explicitly None,
        # which .get()'s default only covers when the key is absent.
        shot_size = shot_info.get("shot_size") or "MS"
        angle = shot_info.get("angle") or "Eye Level"
        lens = shot_info.get("lens") or "50mm"
        movement = shot_info.get("movement") or "Static"
        lighting = shot_info.get("lighting") or "Natural"
        emotion = shot_info.get("emotion") or "Neutral"

        specs_text = f"SHOT: {shot_info.get('shot_number') or 1}  |  {shot_size}  |  {angle}  |  {lens}  |  {movement}  |  {lighting}  |  {emotion.upper()}"
        draw.text((30, height - 28), specs_text, fill=(150, 255, 200, 200))
        
        # Prompt wrap text
        max_chars = 90
        prompt_preview = prompt[:160] + "..." if len(prompt) > 160 else prompt
        prompt_lines = [prompt_preview[i:i+max_chars] for i in range(0, len(prompt_preview), max_chars)]
        
        y_offset = height - 100
        for line in prompt_lines:
            draw.text((50, y_offset), f"PROMPT: {line}", fill=(220, 220, 220, 180))
            y_offset += 16
            
        img.convert("RGB").save(file_path, "PNG")
        return f"/static/storyboards/{filename}"
