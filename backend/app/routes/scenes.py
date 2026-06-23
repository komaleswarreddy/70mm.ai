from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app import models, schemas

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
