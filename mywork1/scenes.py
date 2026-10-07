import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app import models, schemas, ai_service
from app.shot_planner import infer_characters_in_shot

router = APIRouter(prefix="/scenes", tags=["scenes"])

@router.get("/", response_model=List[schemas.SceneResponse])
async def list_scenes(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Scene)
        .options(
            selectinload(models.Scene.action_blocks),
            selectinload(models.Scene.dialogues),
            selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Scene.project_id == project_id)
        .order_by(models.Scene.order.asc(), models.Scene.scene_number.asc())
    )
    return result.scalars().all()

@router.get("/{id}", response_model=schemas.SceneResponse)
async def get_scene(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Scene)
        .options(
            selectinload(models.Scene.action_blocks),
            selectinload(models.Scene.dialogues),
            selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Scene.id == id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene

@router.put("/{id}", response_model=schemas.SceneResponse)
async def update_scene(id: str, scene_update: schemas.SceneUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Scene)
        .options(
            selectinload(models.Scene.action_blocks),
            selectinload(models.Scene.dialogues),
            selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Scene.id == id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
        
    for var, value in scene_update.model_dump(exclude_unset=True).items():
        setattr(scene, var, value)
        
    await db.commit()
    await db.refresh(scene)
    return scene

@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_scenes(request: schemas.ReorderRequest, db: AsyncSession = Depends(get_db)):
    for idx, s_id in enumerate(request.ids):
        result = await db.execute(select(models.Scene).filter(models.Scene.id == s_id))
        scene = result.scalar_one_or_none()
        if scene:
            scene.order = idx
    await db.commit()
    return None

@router.post("/{id}/understand", response_model=schemas.SceneResponse)
async def understand_scene(id: str, db: AsyncSession = Depends(get_db)):
    """Stage 3: scene understanding (emotion, conflict, objects, visual
    emphasis, continuity). Requires Stage 1 (project /parse) to have run
    first. Earlier scenes in the same project (by scene_number) are passed
    as compact continuity context so this scene can correctly reference
    "same jacket as scene 4"-style callbacks."""
    result = await db.execute(select(models.Scene).filter(models.Scene.id == id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    earlier = await db.execute(
        select(models.Scene)
        .filter(models.Scene.project_id == scene.project_id, models.Scene.scene_number < scene.scene_number)
        .order_by(models.Scene.scene_number.asc())
    )
    prior_lines = []
    for s in earlier.scalars().all():
        objs = ", ".join(json.loads(s.key_objects)) if s.key_objects else "none"
        prior_lines.append(f"Scene {s.scene_number} ({s.heading}): key objects = {objs}")

    scene_payload = {
        "scene_number": scene.scene_number,
        "heading": scene.heading,
        "location": scene.location,
        "time_of_day": scene.time_of_day,
        "raw_action": scene.raw_action,
        "raw_dialogue": json.loads(scene.raw_dialogue) if scene.raw_dialogue else [],
        "characters_present": json.loads(scene.characters_present) if scene.characters_present else [],
    }

    results = await ai_service.understand_scenes(
        [scene_payload], batch_size=1, initial_prior_context="\n".join(prior_lines)
    )
    understanding = results.get(scene.scene_number, {})

    scene.action_summary = understanding.get("action_summary")
    scene.emotion = understanding.get("emotion")
    scene.conflict = understanding.get("conflict") or None
    scene.key_objects = json.dumps(understanding.get("key_objects", []))
    scene.visual_emphasis = understanding.get("visual_emphasis")
    scene.continuity_notes = json.dumps(understanding.get("continuity_notes", []))

    await db.commit()
    await db.refresh(scene)
    return scene

@router.post("/{id}/shots/generate-plan", response_model=List[schemas.ShotResponse])
async def generate_shot_plan(id: str, db: AsyncSession = Depends(get_db)):
    """Stage 4 + 5 combined per spec: automatic shot division (rules-first,
    LLM-refined, each shot carrying a required `reasoning`) plus the full
    cinematography plan per shot. Replaces any existing shots for this scene
    — this is a (re)generation endpoint, not an incremental add."""
    result = await db.execute(select(models.Scene).filter(models.Scene.id == id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    is_first_scene_at_location = True
    if scene.location:
        earlier_same_location = await db.execute(
            select(models.Scene).filter(
                models.Scene.project_id == scene.project_id,
                models.Scene.scene_number < scene.scene_number,
                models.Scene.location.isnot(None),
                models.Scene.location.ilike(scene.location),
            )
        )
        is_first_scene_at_location = earlier_same_location.scalar_one_or_none() is None
    else:
        is_first_scene_at_location = scene.scene_number == 1

    scene_payload = {
        "heading": scene.heading,
        "characters_present": json.loads(scene.characters_present) if scene.characters_present else [],
        "raw_action": scene.raw_action,
        "key_objects": json.loads(scene.key_objects) if scene.key_objects else [],
        "emotion": scene.emotion,
        "conflict": scene.conflict,
        "visual_emphasis": scene.visual_emphasis,
    }

    planned_shots = await ai_service.generate_shot_plan(scene_payload, is_first_scene_at_location)

    # Replace existing shots for this scene (ORM delete so cascade to
    # storyboard_frames actually fires, matching /parse's scene replacement).
    existing = await db.execute(
        select(models.Shot).options(selectinload(models.Shot.storyboard_frames)).filter(models.Shot.scene_id == id)
    )
    for old_shot in existing.scalars().all():
        await db.delete(old_shot)
    await db.flush()

    day_night = scene.time_of_day if scene.time_of_day and "night" in scene.time_of_day.lower() else "Day"
    scene_characters = json.loads(scene.characters_present) if scene.characters_present else []

    new_shots = []
    for idx, shot_data in enumerate(planned_shots):
        lighting = shot_data.get("lighting") or {}
        characters_in_shot = infer_characters_in_shot(
            shot_data.get("shot_type"), shot_data.get("reasoning"), scene_characters
        )
        db_shot = models.Shot(
            scene_id=id,
            shot_number=idx + 1,
            order=idx,
            shot_type=shot_data.get("shot_type"),
            reasoning=shot_data.get("reasoning"),
            characters_in_shot=json.dumps(characters_in_shot),
            shot_size=shot_data.get("shot_size"),
            angle=shot_data.get("camera_angle"),
            lens=f"{shot_data['lens_mm']}mm" if shot_data.get("lens_mm") else None,
            movement=shot_data.get("movement"),
            camera_height=shot_data.get("camera_height"),
            framing=shot_data.get("framing"),
            composition_notes=shot_data.get("composition_notes"),
            lighting=lighting.get("key"),  # existing plain-string column the frontend renders
            lighting_detail=json.dumps(lighting),
            emotion=shot_data.get("mood"),  # "mood" (spec) and this app's existing "emotion" column are the same concept
            color_palette=shot_data.get("color_palette"),
            contrast=shot_data.get("contrast"),
            depth_of_field=shot_data.get("depth_of_field"),
            perspective_notes=shot_data.get("perspective_notes"),
            day_night=day_night,
            status="Pending",
        )
        db.add(db_shot)
        new_shots.append(db_shot)

    await db.commit()
    for s in new_shots:
        await db.refresh(s)
    return new_shots

@router.post("/{id}/validate-continuity")
async def validate_scene_continuity_endpoint(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Scene)
        .options(
            selectinload(models.Scene.action_blocks),
            selectinload(models.Scene.dialogues),
            selectinload(models.Scene.shots)
        )
        .filter(models.Scene.id == id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    scene_data = {
        "id": scene.id,
        "heading": scene.heading,
        "action_blocks": [{"content": ab.content} for ab in scene.action_blocks],
        "dialogues": [{"character_name": d.character_name, "content": d.content} for d in scene.dialogues]
    }
    
    shots_data = []
    for s in scene.shots:
        shots_data.append({
            "id": s.id,
            "shot_number": s.shot_number,
            "shot_size": s.shot_size,
            "angle": s.angle,
            "movement": s.movement,
            "lens": s.lens,
            "lighting": s.lighting,
            "day_night": s.day_night,
            "notes": s.notes,
            "visual_tip": s.visual_tip
        })
        
    from app import ai_service
    analysis = await ai_service.validate_scene_continuity(scene_data, shots_data)
    return {"warnings": analysis}
