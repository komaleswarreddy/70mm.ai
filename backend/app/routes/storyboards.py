import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app import models, schemas, ai_service
from app.image_service import ImageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storyboards", tags=["storyboards"])
image_service = ImageService()

@router.post("/{shot_id}/generate", response_model=schemas.StoryboardFrameResponse)
async def generate_frame(shot_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.scene))
        .filter(models.Shot.id == shot_id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    scene_heading = shot.scene.heading
    
    prompt_data = await ai_service.build_image_prompt(
        shot_size=shot.shot_size or "Medium Shot",
        lens=shot.lens or "50mm",
        emotion=shot.emotion or "Neutral",
        lighting=shot.lighting or "Natural",
        movement=shot.movement or "Static",
        action=shot.notes or "A character in a film scene."
    )
    
    positive_prompt = prompt_data.get("positive_prompt", "")
    negative_prompt = prompt_data.get("negative_prompt", "")
    
    frame_result = await db.execute(
        select(models.StoryboardFrame).filter(models.StoryboardFrame.shot_id == shot_id)
    )
    frame = frame_result.scalar_one_or_none()
    if not frame:
        frame = models.StoryboardFrame(shot_id=shot_id)
        db.add(frame)
        await db.flush()
        
    frame.status = "pending"
    frame.prompt = positive_prompt
    frame.negative_prompt = negative_prompt
    await db.commit()
    
    try:
        shot_info = {
            "shot_number": shot.shot_number,
            "shot_size": shot.shot_size,
            "angle": shot.angle,
            "lens": shot.lens,
            "movement": shot.movement,
            "lighting": shot.lighting,
            "emotion": shot.emotion
        }
        image_url = await image_service.generate_storyboard(
            shot_id=shot.id,
            scene_heading=scene_heading,
            shot_info=shot_info,
            prompt=positive_prompt,
            negative_prompt=negative_prompt
        )
        
        frame.image_url = image_url
        frame.status = "completed"
    except Exception as e:
        frame.status = "failed"
        logger.error(f"Failed generating image: {str(e)}")
        
    await db.commit()
    await db.refresh(frame)
    return frame

@router.get("/project/{project_id}", response_model=List[schemas.StoryboardFrameResponse])
async def list_project_frames(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.StoryboardFrame)
        .join(models.Shot)
        .join(models.Scene)
        .filter(models.Scene.project_id == project_id)
        .order_by(models.Scene.order.asc(), models.Shot.order.asc())
    )
    return result.scalars().all()
