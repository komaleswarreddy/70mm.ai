"""
Stage 6 — character asset & consistency system: builds and locks a
character's reference bible (spec: canonical description + 1-4 locked
reference images + a stored identity embedding).

Hard rule from the spec: "never generate a character's first appearance
without first creating and locking their reference set." This module is
the one place that rule gets enforced/fulfilled — routes/characters.py's
lock-reference endpoint is a thin wrapper around it.
"""
import os
import random
import logging
from typing import Any, Dict, List, Optional

from app.embedding_service import compute_image_embedding
from app.image_service import ImageService, CHARACTER_REFS_DIR
from app.shot_prompt_builder import NEGATIVE_PROMPT_BASE

logger = logging.getLogger(__name__)

image_service = ImageService()

# Locked reference portraits went through a completely separate, thinner
# path than shot generation (see lock_character_reference below) -- no
# photorealism cue, and an entirely EMPTY negative prompt (not even
# NEGATIVE_PROMPT_BASE's anti-artifact terms), which was a confirmed
# contributor to portraits coming out both illustrated-looking and
# facially generic ("AI face": symmetric, idealized, stock-photo-like)
# rather than a specific, authentic individual. Reuses NEGATIVE_PROMPT_BASE
# (same anti-illustration terms as shot generation) plus terms specifically
# targeting the generic/idealized "AI face" look.
CHARACTER_PORTRAIT_NEGATIVE_PROMPT = (
    NEGATIVE_PROMPT_BASE + ", symmetrical face, doll-like, generic model, stock photo, "
    "glamour photography, posed studio headshot, uncanny valley, overly smooth skin, perfect skin"
)


# USO conditions on up to USO_MAX_REFERENCE_IMAGES (4) references at once, but
# this service only ever produced ONE per character -- identity was asked to
# hold across every camera angle in the film from a single fixed view.
#
# Measured consequence: with one three-quarter reference, the same character
# scored 0.551-0.886 across 18 shots, and the worst cases were the frames whose
# head angle differed most from it (a clean profile measured 0.500 before any
# identity pass, and only 0.607 after one).
#
# Locking one reference per major head angle gives the conditioning chain a
# matching view whatever the shot calls for. These are the three angles the
# composition pass actually produces. Every one is a medium/waist-up frame,
# never a tight close-up, because the reference's own crop propagates into the
# generated shot.
REFERENCE_ANGLES = (
    "medium shot showing head and torso with space around the subject, body turned "
    "three-quarters away from camera, looking off-camera mid-action, off-centre composition",
    "medium shot showing head and torso, facing the camera directly, calm neutral expression",
    "medium shot showing head and torso, clean side profile view with the face fully in "
    "profile, looking across the frame",
)


async def lock_character_reference(
    character_id: str,
    character_name: str,
    character_description: Optional[str],
    uploaded_images: Optional[List[bytes]] = None,
    wardrobe: str = "",
    period: str = "",
) -> Dict[str, Any]:
    """
    Returns {"reference_image_paths": [...], "embedding_vector": [...] | None, "locked_seed": int | None}.

    If `uploaded_images` is given (user-supplied/consented photos — the
    spec's only allowed source besides frozen-seed generation), saves and
    locks those directly. Otherwise generates one reference image with a
    freshly chosen seed and freezes that exact seed, so re-locking later
    with the same seed reproduces the same reference.
    """
    disk_paths: List[str] = []
    url_paths: List[str] = []
    locked_seed: Optional[int] = None

    if uploaded_images:
        for i, img_bytes in enumerate(uploaded_images[:4]):  # spec: 1-4 references
            filename = f"{character_id}_{i}.png"
            file_path = os.path.join(CHARACTER_REFS_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            disk_paths.append(file_path)
            url_paths.append(f"/static/character_refs/{filename}")
    else:
        locked_seed = random.randint(1, 2**31 - 1)
        # "Character portrait of {name}." alone (the previous prompt) gave
        # the model zero style/realism guidance -- it supplied only the
        # subject, never how to render it, so the base model's default
        # bias (illustrated, idealized/symmetric) went unchallenged. The
        # candid/photographic framing below directly targets the "looks
        # too posed/staged, not a natural photo" note this was built from.
        # Framing matters as much as content here. Flux Kontext reference
        # conditioning reproduces the reference image's own crop and pose, so a
        # tight centred headshot reference forces every downstream shot to come
        # out as a tight centred headshot no matter what action the shot's text
        # describes -- live-observed across a full 20-shot batch, where wide
        # shots, two-shots and over-the-shoulder setups all rendered as the same
        # face-to-camera close-up. Asking for a waist-up, off-centre, looking-
        # away frame keeps the face large enough to carry identity while giving
        # the reference no tight-close-up composition to impose.
        # One reference per head angle (REFERENCE_ANGLES). Each derives its own
        # seed from the single stored locked_seed, so the set varies by angle
        # yet stays reproducible.
        for index, angle in enumerate(REFERENCE_ANGLES):
            # This exact wording produced the approved RAM/SITA references. A
            # positive-only rewrite (no "not ..." phrases) was tried 2026-09-30
            # together with lower guidance and rejected, so it is kept as is;
            # period and wardrobe are appended only when the project sets them.
            prompt = (
                f"Candid unposed photograph of {character_name}. {character_description or ''} "
                f"{angle}, natural environment behind them, cinematic available light, shot on "
                "35mm film, real skin texture and natural asymmetry, photorealistic -- not a "
                "tight close-up, not a centred studio headshot"
            ).strip()
            if wardrobe:
                prompt += f". Wearing {wardrobe.strip().rstrip('.')}"
            if period:
                prompt += f". Set in {period}"
            url = await image_service.generate_character_portrait(
                character_id, index, prompt, locked_seed + index,
                negative_prompt=CHARACTER_PORTRAIT_NEGATIVE_PROMPT,
            )
            url_paths.append(url)
            disk_paths.append(os.path.join(CHARACTER_REFS_DIR, f"{character_id}_{index}.png"))

    embedding_vector = compute_image_embedding(disk_paths[0]) if disk_paths else None
    if disk_paths and embedding_vector is None:
        logger.warning(f"Could not compute identity embedding for character {character_id} - CLIP model unavailable.")

    return {
        "reference_image_paths": url_paths,
        "embedding_vector": embedding_vector,
        "locked_seed": locked_seed,
    }
