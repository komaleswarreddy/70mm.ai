import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app import models, schemas, ai_service
from app.stage7_orchestrator import generate_shot_image, CharactersNotLockedError, _resolve_characters_in_shot, _parse_lens_mm
from app.continuity_service import check_shot_continuity

router = APIRouter(prefix="/shots", tags=["shots"])

# ── Collection routes (must come BEFORE /{id} param routes) ──────────────────

@router.get("/", response_model=List[schemas.ShotResponse])
async def list_shots(scene_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.storyboard_frames))
        .filter(models.Shot.scene_id == scene_id)
        .order_by(models.Shot.order.asc(), models.Shot.shot_number.asc())
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.ShotResponse, status_code=status.HTTP_201_CREATED)
async def create_shot(scene_id: str, shot: schemas.ShotCreate, db: AsyncSession = Depends(get_db)):
    scene_result = await db.execute(select(models.Scene).filter(models.Scene.id == scene_id))
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
        
    db_shot = models.Shot(
        scene_id=scene_id,
        shot_number=shot.shot_number,
        shot_size=shot.shot_size,
        angle=shot.angle,
        movement=shot.movement,
        lens=shot.lens,
        lighting=shot.lighting,
        emotion=shot.emotion,
        color_palette=shot.color_palette,
        visual_tip=shot.visual_tip,
        notes=shot.notes,
        order=shot.order,
        shooting_order=shot.shooting_order or 0,
        location_order=shot.location_order,
        day_night=shot.day_night or "Day",
        duration=shot.duration or 0,
        status=shot.status or "Pending",
        color_label=shot.color_label,
        board_caption=shot.board_caption,
        board_dialogue=shot.board_dialogue,
        board_crop=shot.board_crop,
    )
    db.add(db_shot)
    await db.commit()
    await db.refresh(db_shot)
    
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.storyboard_frames))
        .filter(models.Shot.id == db_shot.id)
    )
    return result.scalar_one()

@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_shots(request: schemas.ReorderRequest, db: AsyncSession = Depends(get_db)):
    for idx, s_id in enumerate(request.ids):
        result = await db.execute(select(models.Shot).filter(models.Shot.id == s_id))
        shot = result.scalar_one_or_none()
        if shot:
            shot.order = idx
    await db.commit()
    return None

@router.put("/batch", response_model=List[schemas.ShotResponse])
async def batch_update_shots(batch: schemas.ShotBatchUpdate, db: AsyncSession = Depends(get_db)):
    """Batch update multiple shots at once — route MUST be before /{id}."""
    updated_shots = []
    for s_id in batch.ids:
        result = await db.execute(
            select(models.Shot)
            .options(selectinload(models.Shot.storyboard_frames))
            .filter(models.Shot.id == s_id)
        )
        shot = result.scalar_one_or_none()
        if shot:
            for var, value in batch.updates.model_dump(exclude_unset=True).items():
                setattr(shot, var, value)
            updated_shots.append(shot)
    await db.commit()
    for shot in updated_shots:
        await db.refresh(shot)
    return updated_shots

# ── Item routes (/{id} param — must come AFTER static routes) ────────────────

@router.get("/{id}", response_model=schemas.ShotResponse)
async def get_shot(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.storyboard_frames))
        .filter(models.Shot.id == id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot

@router.put("/{id}", response_model=schemas.ShotResponse)
async def update_shot(id: str, shot_update: schemas.ShotUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.storyboard_frames))
        .filter(models.Shot.id == id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    for var, value in shot_update.model_dump(exclude_unset=True).items():
        setattr(shot, var, value)
        
    await db.commit()
    await db.refresh(shot)
    return shot

_EDIT_FIELD_TO_SHOT_ATTR = {
    "shot_type": "shot_type", "shot_size": "shot_size", "angle": "angle",
    "movement": "movement", "camera_height": "camera_height", "framing": "framing",
    "composition_notes": "composition_notes", "contrast": "contrast",
    "depth_of_field": "depth_of_field", "perspective_notes": "perspective_notes",
    "color_palette": "color_palette", "day_night": "day_night",
    "mood": "emotion",  # spec's "mood" is this app's existing "emotion" column, same as Stage 5
    # "lens_mm" handled separately — Shot.lens is a display string ("35mm"), not a bare int.
}

@router.patch("/{id}/edit", response_model=schemas.ShotResponse)
async def edit_shot(id: str, edit_input: schemas.ShotEditInput, db: AsyncSession = Depends(get_db)):
    """Stage 10: translates a natural-language instruction ("make this a
    low-angle shot", "use a 50mm lens", "move camera behind the character")
    into a structured diff via the LLM (repair-loop validated, deterministic
    keyword fallback if AI is unavailable), applies ONLY the changed
    fields, and re-queues Stage 7 generation for just this shot."""
    result = await db.execute(select(models.Shot).filter(models.Shot.id == id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    current_shot = {
        "shot_type": shot.shot_type, "shot_size": shot.shot_size, "angle": shot.angle,
        "lens_mm": _parse_lens_mm(shot.lens), "movement": shot.movement,
        "camera_height": shot.camera_height, "framing": shot.framing,
        "composition_notes": shot.composition_notes, "contrast": shot.contrast,
        "depth_of_field": shot.depth_of_field, "perspective_notes": shot.perspective_notes,
        "color_palette": shot.color_palette, "mood": shot.emotion, "day_night": shot.day_night,
    }

    diff = await ai_service.translate_shot_edit(current_shot, edit_input.instruction)

    for field, value in diff.items():
        if field == "lens_mm":
            shot.lens = f"{value}mm"
        else:
            setattr(shot, _EDIT_FIELD_TO_SHOT_ATTR[field], value)

    await db.commit()

    try:
        await generate_shot_image(db, id)
    except CharactersNotLockedError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await db.execute(
        select(models.Shot).options(selectinload(models.Shot.storyboard_frames)).filter(models.Shot.id == id)
    )
    return result.scalar_one()

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Shot).filter(models.Shot.id == id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    await db.delete(shot)
    await db.commit()
    return None

@router.post("/{id}/generate-image", response_model=schemas.StoryboardFrameResponse)
async def generate_image(id: str, db: AsyncSession = Depends(get_db)):
    """Stage 7 route exactly as named in the spec's route table — runs the
    same pipeline as POST /storyboards/{shot_id}/generate (the route the
    frontend actually calls); see stage7_orchestrator.generate_shot_image."""
    try:
        return await generate_shot_image(db, id)
    except CharactersNotLockedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{id}/continuity-check", response_model=schemas.ContinuityCheckResponse)
async def continuity_check(id: str, reinforced_regenerate: bool = False, db: AsyncSession = Depends(get_db)):
    """Stage 9: character-identity, style-drift, and color-grade checks
    against the rest of the scene. Pure by default — flags/persists
    needs_review + continuity_score but never regenerates anything unless
    `reinforced_regenerate=true` is explicitly passed AND a flag was found,
    in which case it runs exactly one regeneration attempt at reinforced
    consistency strength and re-checks the new image."""
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.scene), selectinload(models.Shot.storyboard_frames))
        .filter(models.Shot.id == id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    scene = shot.scene

    async def run_check():
        frame = next((f for f in shot.storyboard_frames if f.status == "completed" and f.image_url), None)
        characters = await _resolve_characters_in_shot(db, shot, scene)
        character_embeddings = [
            {"name": c.name, "embedding_vector": json.loads(c.embedding_vector) if c.embedding_vector else None}
            for c in characters
        ]
        other_shots = await db.execute(
            select(models.Shot).options(selectinload(models.Shot.storyboard_frames))
            .filter(models.Shot.scene_id == scene.id, models.Shot.id != id)
        )
        other_image_urls = []
        for s in other_shots.scalars().all():
            f = next((fr for fr in s.storyboard_frames if fr.status == "completed" and fr.image_url), None)
            if f:
                other_image_urls.append(f.image_url)
        return check_shot_continuity(frame.image_url if frame else None, character_embeddings, other_image_urls)

    check_result = await run_check()
    regenerated = False

    if check_result["needs_review"] and reinforced_regenerate:
        try:
            await generate_shot_image(db, id, consistency_strength=0.9)
            regenerated = True
            await db.refresh(shot)
            check_result = await run_check()
        except CharactersNotLockedError:
            pass  # can't reinforce an unlocked character — keep the original check result

    shot.needs_review = 1 if check_result["needs_review"] else 0
    shot.continuity_score = int(check_result["identity_score"] * 1000) if check_result["identity_score"] is not None else None
    await db.commit()

    return schemas.ContinuityCheckResponse(
        shot_id=id,
        needs_review=check_result["needs_review"],
        flags=check_result["flags"],
        identity_score=check_result["identity_score"],
        color_distance=check_result["color_distance"],
        regenerated=regenerated,
    )

@router.get("/{id}/muse-history", response_model=List[schemas.DirectorMuseHistoryResponse])
async def list_muse_history(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.DirectorMuseHistory)
        .filter(models.DirectorMuseHistory.shot_id == id)
        .order_by(models.DirectorMuseHistory.timestamp.desc())
    )
    return result.scalars().all()
