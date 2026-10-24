"""
Stage 7 — deterministic image-generation prompt builder.

Spec requirement: "build this as a template function, not free-text LLM
prose, so results stay controllable and debuggable." Built directly from
Stage 5's cinematography record + Stage 3's scene description + each
present character's LOCKED description (never invented likeness text).
No LLM call anywhere in this file.
"""
import json
from typing import Any, Dict, List, Optional

# NOTE: every graph in comfy_workflow_builder samples at cfg 1.0 (Flux takes its
# guidance from FluxGuidance), and ComfyUI skips the negative/uncond pass
# entirely at cfg 1.0 (comfy/samplers.py sampling_function). So this text has NO
# effect on current output -- realism must be steered by the positive prompt
# and FluxGuidance. Kept for any caller that samples with cfg > 1.
NEGATIVE_PROMPT_BASE = (
    "blurry, distorted, deformed, extra limbs, extra fingers, mutated hands, "
    "text, watermark, signature, low quality, worst quality, jpeg artifacts, "
    # Style-exclusion terms -- added because nothing here previously fought
    # the (now-removed) "storyboard illustration" cue below; without an
    # explicit push away from illustrated/painterly mediums, Flux has
    # nothing to bias it back toward photorealism.
    "illustration, painting, drawing, cartoon, anime, concept art, comic book, "
    "sketch, digital art, 3d render, cgi render, plastic skin, airbrushed, "
    "line art, flat shading, "
    # Anatomy and wardrobe terms, added after live output showed a duplicated
    # forearm, twisted wrists and a character rendered without a shirt. The
    # generic "extra limbs/mutated hands" terms above were demonstrably not
    # enough on their own.
    "shirtless, topless, bare chest, undressed, missing clothing, "
    "extra arms, extra hands, duplicated limbs, three arms, floating limbs, "
    "twisted wrist, bent backwards joint, fused fingers, too many fingers, "
    "malformed hands, deformed fingers, melted hands, disconnected limbs"
)

# The photorealism cue that produced the approved shots. A longer "real skin /
# lived-in clothes / film grain" variant was tried 2026-09-30 and rolled back
# with the lower-guidance experiment; this is the validated wording.
REALISM_CUE = "cinematic film still, photorealistic, shot on 35mm film, natural skin texture, professional cinematography"

# Stage 4/5's deterministic fallback (when every LLM provider fails) writes
# human-readable status text into fields like composition_notes/framing —
# useful in a UI, meaningless (or actively confusing) as prompt content for
# an image model. Drop any field containing these markers from the prompt.
_FALLBACK_TEXT_MARKERS = ("unavailable", "fallback")


def resolve_wardrobe(wardrobe_json: Optional[str], scene_number: Optional[int]) -> str:
    """The outfit a character wears in a given scene: that scene's entry in
    Character.wardrobe["by_scene"] if present, else its "default", else ""."""
    if not wardrobe_json:
        return ""
    try:
        data = json.loads(wardrobe_json)
    except (TypeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    by_scene = data.get("by_scene") or {}
    if scene_number is not None and str(scene_number) in by_scene:
        return str(by_scene[str(scene_number)] or "")
    return str(data.get("default") or "")


def _is_real_content(text: Optional[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return not any(marker in lowered for marker in _FALLBACK_TEXT_MARKERS)


def build_shot_prompt(
    shot: Dict[str, Any],
    scene: Dict[str, Any],
    characters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    `shot`: a Stage 4/5 shot record (shot_size, camera_angle, lens_mm,
    movement, framing, composition_notes, lighting_detail dict, mood/
    emotion, color_palette).
    `scene`: Stage 1 + 3 fields (heading, visual_emphasis).
    `characters`: locked Character rows present in this shot — {"name",
    "description", optional "wardrobe" already resolved for this scene} —
    used for their canonical description only, never a
    real person's likeness (per the spec's non-fabrication rule; identity
    itself is conditioned separately via USO, not prompt text).

    Returns {"positive_prompt": str, "negative_prompt": str}.
    """
    parts: List[str] = []

    shot_size = shot.get("shot_size") or "Medium Shot"
    camera_angle = shot.get("camera_angle") or "eye level"
    parts.append(f"{shot_size}, {camera_angle} angle")
    # A long character description reads to Flux as "this is a portrait" and
    # pulls wide shots in to medium or close framing (observed on sc1s1). Wide
    # shots say explicitly how big the people are.
    if any(t in shot_size.lower() for t in ("wide", "establishing", "extreme long", "long shot")):
        parts.append("the people are small full-length figures within a large environment that fills the frame")

    if shot.get("lens_mm"):
        parts.append(f"{shot['lens_mm']}mm lens")
    movement = shot.get("movement")
    if movement and movement.lower() != "static":
        parts.append(f"{movement} camera movement")

    heading = scene.get("heading")
    if heading:
        parts.append(heading.title())
    if scene.get("period"):
        parts.append(f"set in {scene['period']}")
    # The scene's visual_emphasis describes the scene's key beat ("focus on
    # the moment Ram discovers the plain envelope"). Applied to every shot it
    # dragged wide establishing shots onto that beat -- one reason "Wide Shot"
    # frames rendered as close-ups. A shot's own framing/composition notes are
    # the more specific instruction, so the scene emphasis is only a fallback.
    has_own_staging = _is_real_content(shot.get("framing")) or _is_real_content(shot.get("composition_notes"))
    if not has_own_staging and _is_real_content(scene.get("visual_emphasis")):
        parts.append(scene["visual_emphasis"])
    if _is_real_content(shot.get("framing")):
        parts.append(shot["framing"])
    if _is_real_content(shot.get("composition_notes")):
        parts.append(shot["composition_notes"])

    # Stage 4's `reasoning` (why this shot/what it depicts) and any free-form
    # `notes` (actor/blocking direction) are the ONLY place a shot's actual
    # described action/pose lives -- everything above this point is generic
    # cinematography metadata that two shots in the same scene can share
    # even when they depict opposite actions. Previously never read at all,
    # which is why same-scene shots could produce a byte-identical prompt
    # regardless of what was actually supposed to happen in each one.
    action_parts = []
    if _is_real_content(shot.get("notes")):
        action_parts.append(shot["notes"].strip())
    if _is_real_content(shot.get("reasoning")):
        action_parts.append(shot["reasoning"].strip())
    if action_parts:
        parts.append(" ".join(action_parts))

    # Multi-character shots need to say plainly that more than one person
    # shares the frame. Listing each character as its own comma-separated
    # phrase ("RAM: <desc>, SITA: <desc>") reads to the model as a pile of
    # attributes for one subject, not as two people -- live-observed: a
    # two-shot whose text said "Show both Sita and Ram" rendered Sita alone,
    # while a shot whose composition_notes explicitly staged both
    # ("Foreground: Ram, background: Sita") rendered both correctly.
    def _who(c: Dict[str, Any]) -> str:
        desc = (c.get("description") or "").strip()
        wardrobe = (c.get("wardrobe") or "").strip()
        return " ".join(p for p in (desc, f"Wearing {wardrobe}" if wardrobe else "") if p)

    named = [c for c in (characters or [])]
    if len(named) > 1:
        who = " and ".join(f"{c['name']} ({_who(c)})" if _who(c) else c["name"] for c in named)
        parts.append(f"{len(named)} people together in the same frame, both fully visible: {who}")
    else:
        for c in named:
            parts.append(f"{c['name']}: {_who(c)}" if _who(c) else c["name"])

    # A sentence telling the model to "use the reference images only for
    # facial identity; do not copy their pose, clothing, framing" used to be
    # appended here. Removed: the composition pass receives NO reference images
    # at all, and Flux's T5 encoder does not reliably honour negation, so the
    # sentence only injected "pose / clothing / framing" concepts into shots.

    lighting = shot.get("lighting_detail") or {}
    if isinstance(lighting, dict) and lighting:
        quality = lighting.get("quality", "soft")
        direction = lighting.get("direction", "front")
        parts.append(f"{quality} key light from the {direction}")
        practicals = str(lighting.get("practicals") or "").strip()
        if practicals and practicals.lower() not in ("none", "n/a", "null", "no"):
            parts.append(f"practical lighting: {practicals}")
        if lighting.get("color_temp_k"):
            parts.append(f"{lighting['color_temp_k']}K color temperature")

    mood = shot.get("mood") or shot.get("emotion")
    if mood:
        parts.append(f"{mood} mood")
    if shot.get("color_palette"):
        parts.append(f"{shot['color_palette']} color palette")
    if shot.get("contrast"):
        parts.append(f"{shot['contrast'].lower()} contrast")
    if shot.get("depth_of_field"):
        parts.append(f"{shot['depth_of_field'].lower()} depth of field")

    parts.append(REALISM_CUE)
    positive_prompt = ", ".join(p.strip() for p in parts if p and p.strip())
    return {"positive_prompt": positive_prompt, "negative_prompt": NEGATIVE_PROMPT_BASE}
