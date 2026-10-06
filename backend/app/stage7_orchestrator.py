"""
Stage 7 orchestration — shared by both routes/storyboards.py's existing
POST /storyboards/{shot_id}/generate (the one the frontend actually calls)
and the spec-literal POST /shots/{id}/generate-image, so the real pipeline
lives in exactly one place.

Builds the deterministic prompt (shot_prompt_builder), resolves which
locked characters are in the shot (character_consistency — raises if any
aren't locked yet, per the spec's hard rule), and calls image_service for
generation with retry + Pillow fallback.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models
from app.shot_prompt_builder import build_shot_prompt, resolve_wardrobe
from app.character_consistency.character_consistency import CharacterConsistencyOrchestrator
from app import face_identity
from app.image_qa import assess_shot
from app.image_service import ImageService

logger = logging.getLogger(__name__)

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))

# How many times a shot may be regenerated when the quality gate finds a
# BLOCKING defect (anatomy, wardrobe, missing character). Each attempt is a
# fresh seed; cosmetic-only findings never trigger a retry.
MAX_QA_ATTEMPTS = 3

# Shot sizes where the characters are incidental scenery rather than the
# subject -- an establishing wide of a mountain outpost or an insert of a
# letter has no business being retried for "not enough faces".
_WIDE_OR_DETAIL_SHOT_SIZES = ("wide", "establishing", "extreme", "insert", "cutaway", "aerial")


# Minimum SFace similarity between a lead's face in a finished shot and that
# character's locked references before the shot is accepted. Calibrated on the
# 2026-09-30 sweep: correctly repainted faces scored 0.61-0.79, the one face a
# viewer read as "a different man" scored 0.45, and different characters score
# ~0.27-0.33 against each other.
FACE_MATCH_GATE = 0.55


def _face_gate_applies(shot_size: str) -> bool:
    """Faces in wide/establishing/insert shots are too small (or absent) for a
    reliable identity score, and extras there would be scored as leads."""
    size = (shot_size or "").lower()
    return not any(token in size for token in _WIDE_OR_DETAIL_SHOT_SIZES)


def _weak_faces(image_path: str, character_refs, priority) -> Dict[str, float]:
    if not character_refs:
        return {}
    scores = face_identity.identity_scores(image_path, character_refs, priority)
    return {name: score for name, score in scores.items() if score < FACE_MATCH_GATE}


def _requires_multiple_people(shot_size: str, character_count: int) -> bool:
    """True when this shot genuinely needs 2+ people visible in frame."""
    if character_count < 2:
        return False
    size = (shot_size or "").lower()
    return not any(token in size for token in _WIDE_OR_DETAIL_SHOT_SIZES)


image_service = ImageService()
consistency_orchestrator = CharacterConsistencyOrchestrator()


class CharactersNotLockedError(Exception):
    """Raised when a shot names characters that haven't been locked yet
    (Stage 6). Routes should turn this into an HTTP 400 pointing at
    POST /characters/{id}/lock-reference — never silently generate an
    unlocked/inconsistent identity."""
    pass


async def _resolve_characters_in_shot(db: AsyncSession, shot: models.Shot, scene: models.Scene) -> List[models.Character]:
    names = json.loads(shot.characters_in_shot) if shot.characters_in_shot else None
    if names is None:  # shot predates Stage 4/5's auto-population — fall back to the whole scene cast
        names = json.loads(scene.characters_present) if scene.characters_present else []
    if not names:
        return []

    result = await db.execute(
        select(models.Character).filter(models.Character.project_id == scene.project_id)
    )
    all_characters = result.scalars().all()
    name_lower_to_char = {c.name.lower(): c for c in all_characters}
    return [name_lower_to_char[n.lower()] for n in names if n.lower() in name_lower_to_char]


def _select_focal_character(shot: models.Shot, characters: List[models.Character]) -> models.Character:
    """Pick the ONE character whose reference image should condition this shot.

    Live-verified bug this fixes: pooling every present character's reference
    into one ReferenceLatent chain (which is what _build_uso_workflow does with
    whatever it's handed) blends them into a single identity space -- there is
    nothing binding a given reference to a given person. In practice that put
    SITA's braid and saree colours onto RAM in every shot the two shared, and
    showed up numerically as a large identity gap: multi-character shots scored
    0.657 average CLIP identity vs 0.828 for single-character ones.

    Conditioning on one character removes the blending entirely. The other
    characters still reach the model -- build_shot_prompt keeps describing all
    of them in the prompt text -- they just aren't reference-conditioned.

    Focal choice: whoever the shot's own text talks about first, checking the
    most specific field first (composition_notes/framing name the subject of
    the frame directly, e.g. "Close, Ram's face, eyes scanning text"), falling
    back to the reasoning, then to shot order.
    """
    if len(characters) == 1:
        return characters[0]

    for field in (shot.composition_notes, shot.framing, shot.reasoning, shot.notes):
        if not field:
            continue
        lowered = field.lower()
        positions = []
        for c in characters:
            # Word-boundary match, NOT a substring search: "RAM" occurs inside
            # ordinary words this text is full of ("frames", "dramatic"), which
            # made a plain find() pick RAM as the focal character of
            # "Frames Sita's reaction to Ram" -- caught by test_focal_character_
            # falls_back_to_reasoning_first_mention.
            match = re.search(r"\b" + re.escape(c.name.lower()) + r"\b", lowered)
            if match:
                positions.append((match.start(), c))
        if positions:
            positions.sort(key=lambda p: p[0])
            return positions[0][1]

    return characters[0]


def _build_qa_expectation(
    shot: models.Shot, scene: models.Scene, characters: List[models.Character]
) -> str:
    """Plain-language description of what this frame is SUPPOSED to show.

    Handed to the vision reviewer so it can judge the frame against intent
    rather than in the abstract -- that is what lets it report "the second
    required character is missing" or "this reads as a close-up, not a wide
    shot", neither of which any local landmark check can see.
    """
    bits = []
    if shot.shot_size:
        bits.append(f"A {shot.shot_size}")
    if shot.angle:
        bits.append(f"at a {shot.angle} angle")
    if scene.heading:
        bits.append(f"in: {scene.heading}")
    header = " ".join(bits) if bits else "A cinematic frame"

    who = ""
    if characters:
        def _described(c):
            bits = [(c.description or "").strip()[:220]]
            outfit = resolve_wardrobe(c.wardrobe, scene.scene_number)
            if outfit:
                bits.append(f"wearing {outfit}")
            text = "; ".join(b for b in bits if b)
            return f"{c.name} ({text})" if text else c.name
        described = "; ".join(_described(c) for c in characters)
        count_phrase = (
            f"ALL {len(characters)} of these characters must be visible in the frame"
            if len(characters) > 1 else "This character must be visible in the frame"
        )
        who = f" {count_phrase}: {described}."

    action = " ".join(p for p in (shot.notes, shot.reasoning) if p)
    action = f" The action depicted: {action}" if action else ""

    return f"{header}.{who}{action}".strip()


async def prepare_shot_generation(
    db: AsyncSession, shot_id: str, consistency_strength: float = 0.7
) -> Dict[str, Any]:
    """Everything needed to generate one shot, as plain values.

    Split out so the single-shot path and the batched runner build prompts,
    resolve characters and pick the focal reference through exactly ONE
    implementation -- duplicating any of that is how the two would silently
    drift apart.

    Every value returned is a plain str/dict/list, never a live ORM instance:
    the caller commits between phases, and reading an expired ORM attribute
    afterwards raises MissingGreenlet under asyncio.
    """
    result = await db.execute(
        select(models.Shot).options(selectinload(models.Shot.scene)).filter(models.Shot.id == shot_id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise ValueError("Shot not found")
    scene = shot.scene

    characters = await _resolve_characters_in_shot(db, shot, scene)

    shot_payload: Dict[str, Any] = {
        "shot_size": shot.shot_size, "camera_angle": shot.angle, "lens_mm": _parse_lens_mm(shot.lens),
        "movement": shot.movement, "framing": shot.framing, "composition_notes": shot.composition_notes,
        "lighting_detail": json.loads(shot.lighting_detail) if shot.lighting_detail else {},
        "mood": shot.emotion, "color_palette": shot.color_palette, "contrast": shot.contrast,
        "depth_of_field": shot.depth_of_field,
        "reasoning": shot.reasoning, "notes": shot.notes,
    }
    period = (await db.execute(
        select(models.Project.period).filter(models.Project.id == scene.project_id)
    )).scalar_one_or_none()
    scene_payload = {"heading": scene.heading, "visual_emphasis": scene.visual_emphasis, "period": period}
    character_payloads = [
        {"name": c.name, "description": c.description, "wardrobe": resolve_wardrobe(c.wardrobe, scene.scene_number)}
        for c in characters
    ]

    prompt_data = build_shot_prompt(shot_payload, scene_payload, character_payloads)

    consistency_params = None
    if characters:
        unlocked = [c.name for c in characters if not c.is_locked]
        if unlocked:
            raise CharactersNotLockedError(
                f"Cannot generate this shot — character(s) not yet locked: {', '.join(unlocked)}. "
                "Call POST /characters/{id}/lock-reference first."
            )
        # Every present character is passed, focal first. They are never pooled
        # into one reference chain (that blended SITA's braid onto RAM): the
        # identity pass repaints each detected face from its OWN character's
        # references only (image_service._apply_identity). Focal order decides
        # who is repainted when fewer faces are found than characters.
        focal = _select_focal_character(shot, characters)
        ordered = [focal] + [c for c in characters if c is not focal]
        try:
            consistency_params = consistency_orchestrator.compile_consistency_params(
                [{
                    "name": c.name,
                    "description": c.description,
                    "reference_image_paths": json.loads(c.reference_image_paths) if c.reference_image_paths else [],
                    "is_locked": bool(c.is_locked),
                } for c in ordered],
                strength=consistency_strength,
            )
        except ValueError as e:
            raise CharactersNotLockedError(str(e)) from e

    return {
        "shot_id": shot.id,
        "scene_heading": scene.heading or "",
        "shot_size": shot.shot_size or "",
        "positive_prompt": prompt_data["positive_prompt"],
        "negative_prompt": prompt_data["negative_prompt"],
        "consistency_params": consistency_params,
        "shot_info": {
            "shot_number": shot.shot_number, "shot_size": shot.shot_size, "angle": shot.angle,
            "lens": shot.lens, "movement": shot.movement, "lighting": shot.lighting,
            "emotion": shot.emotion,
        },
        "expectation": _build_qa_expectation(shot, scene, characters),
        "character_names": [c.name for c in characters],
        "character_count": len(characters),
        "require_people_check": _requires_multiple_people(shot.shot_size or "", len(characters)),
    }


async def generate_shot_image(db: AsyncSession, shot_id: str, consistency_strength: float = 0.7) -> models.StoryboardFrame:
    # prepare_shot_generation returns plain values only, which also satisfies
    # the "capture before commit" rule below -- AsyncSession expires ORM
    # attributes on commit and reading one afterwards raises MissingGreenlet.
    plan = await prepare_shot_generation(db, shot_id, consistency_strength)

    positive_prompt = plan["positive_prompt"]
    negative_prompt = plan["negative_prompt"]
    consistency_params = plan["consistency_params"]
    shot_id_value = plan["shot_id"]
    scene_heading_value = plan["scene_heading"]
    shot_size_value = plan["shot_size"]
    expectation_value = plan["expectation"]
    character_names = plan["character_names"]
    shot_info = plan["shot_info"]
    characters = plan["character_names"]        # only len() is used from here on

    frame_result = await db.execute(select(models.StoryboardFrame).filter(models.StoryboardFrame.shot_id == shot_id))
    frame = frame_result.scalar_one_or_none()
    if not frame:
        frame = models.StoryboardFrame(shot_id=shot_id)
        db.add(frame)
        await db.flush()

    frame.status = "pending"
    frame.prompt = positive_prompt
    frame.negative_prompt = negative_prompt
    await db.commit()

    require_people_check = plan["require_people_check"]
    qa_expectation = expectation_value
    character_refs = {}
    if consistency_params and _face_gate_applies(shot_size_value):
        character_refs = {
            i["name"]: face_identity.reference_features(i.get("reference_image_paths") or [])
            for i in consistency_params.get("identities", [])
        }
        character_refs = {n: r for n, r in character_refs.items() if r}

    try:
        image_url = None
        last_problems: List[str] = []
        last_cosmetic: List[str] = []
        # Every attempt overwrites the same file, so the best one is kept in
        # memory and written back at the end -- a retry must never replace a
        # better frame with a worse one.
        best = None  # (problem_count, image_bytes, problems, cosmetic)

        for attempt in range(1, MAX_QA_ATTEMPTS + 1):
            image_url = await image_service.generate_storyboard(
                shot_id=shot_id_value,
                scene_heading=scene_heading_value,
                shot_info=shot_info,
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                consistency_params=consistency_params,
            )
            if not image_url:
                break

            verdict = assess_shot(
                os.path.join(BACKEND_ROOT, image_url.lstrip("/")),
                expectation=qa_expectation,
                expected_people=max(1, len(characters)),
                require_people_check=require_people_check,
                expected_shot_size=shot_size_value,
                expected_character_names=character_names,
            )
            last_problems = list(verdict.get("problems") or [])
            last_cosmetic = verdict.get("cosmetic") or []

            frame_path = os.path.join(BACKEND_ROOT, image_url.lstrip("/"))
            for name, score in _weak_faces(frame_path, character_refs, character_names).items():
                last_problems.append(
                    f"{name}'s face matches the locked reference at {score:.2f} (gate {FACE_MATCH_GATE})"
                )
            if os.path.exists(frame_path) and (best is None or len(last_problems) < best[0]):
                with open(frame_path, "rb") as fh:
                    best = (len(last_problems), fh.read(), list(last_problems), list(last_cosmetic))

            if not last_problems:
                if last_cosmetic:
                    logger.info(
                        f"Shot {shot_id}: passed QA on attempt {attempt} "
                        f"with cosmetic notes: {last_cosmetic}"
                    )
                break

            if attempt < MAX_QA_ATTEMPTS:
                logger.info(
                    f"Shot {shot_id}: QA found blocking defect(s) {last_problems} "
                    f"— regenerating on a fresh seed (attempt {attempt + 1}/{MAX_QA_ATTEMPTS})."
                )
            else:
                # Deliberately kept rather than discarded: a flagged frame is
                # more useful to a human reviewer than no frame, and the
                # problems are logged so the audit can list it.
                logger.warning(
                    f"Shot {shot_id}: still failing QA after {MAX_QA_ATTEMPTS} attempts "
                    f"{last_problems} — keeping the best attempt and flagging it for review."
                )

        if best is not None and image_url:
            with open(os.path.join(BACKEND_ROOT, image_url.lstrip("/")), "wb") as fh:
                fh.write(best[1])
            last_problems, last_cosmetic = best[2], best[3]
        frame.image_url = image_url
        frame.status = "completed"
        # Shot.needs_review is the existing review flag (Stage 9 already uses
        # it); StoryboardFrame has no such column, so setting it there would
        # silently not persist.
        #
        # Written as an explicit UPDATE rather than `shot.needs_review = ...`:
        # the commit above expired this instance's attributes, and assigning to
        # an expired ORM attribute makes SQLAlchemy load the row first to record
        # attribute history -- an implicit lazy load that raises MissingGreenlet
        # under asyncio. Caught by test_generate_image_locked_single_character_
        # succeeds before it ever ran for real.
        await db.execute(
            update(models.Shot)
            .where(models.Shot.id == shot_id_value)
            .values(needs_review=1 if last_problems else 0)
        )
    except Exception as e:
        frame.status = "failed"
        logger.error(f"Failed generating image for shot {shot_id}: {e}")

    await db.commit()
    await db.refresh(frame)
    return frame


def _parse_lens_mm(lens: Any) -> Any:
    """Shot.lens is stored as a display string like "35mm" — recover the
    plain int for the prompt builder/workflow (falls back to None, which
    both handle gracefully with a sane default)."""
    if not lens:
        return None
    try:
        return int("".join(ch for ch in str(lens) if ch.isdigit()))
    except ValueError:
        return None
