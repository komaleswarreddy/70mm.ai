from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/shots", tags=["shots"])

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
        color_label=shot.color_label
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

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Shot).filter(models.Shot.id == id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    await db.delete(shot)
    await db.commit()
    return None

@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_shots(request: schemas.ReorderRequest, db: AsyncSession = Depends(get_db)):
    for idx, s_id in enumerate(request.ids):
        result = await db.execute(select(models.Shot).filter(models.Shot.id == s_id))
        shot = result.scalar_one_or_none()
        if shot:
            shot.order = idx
    await db.commit()
    return None

@router.get("/{id}/muse-history", response_model=List[schemas.DirectorMuseHistoryResponse])
async def list_muse_history(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.DirectorMuseHistory)
        .filter(models.DirectorMuseHistory.shot_id == id)
        .order_by(models.DirectorMuseHistory.timestamp.desc())
    )
    return result.scalars().all()

@router.put("/batch", response_model=List[schemas.ShotResponse])
async def batch_update_shots(batch: schemas.ShotBatchUpdate, db: AsyncSession = Depends(get_db)):
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
    # Refresh to return standard Response
    for shot in updated_shots:
        await db.refresh(shot)
    return updated_shots

