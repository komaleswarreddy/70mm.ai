import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app import models, schemas
from app.stage7_orchestrator import generate_shot_image, CharactersNotLockedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storyboards", tags=["storyboards"])

@router.post("/{shot_id}/generate", response_model=schemas.StoryboardFrameResponse)
async def generate_frame(shot_id: str, db: AsyncSession = Depends(get_db)):
    """Stage 7: character-consistent (USO) image generation
    via ComfyUI + Flux.1-dev, with retry + Pillow-placeholder fallback. This
    is the route the frontend actually calls — see also the spec-literal
    alias POST /shots/{id}/generate-image in routes/shots.py, which runs
    the exact same pipeline via stage7_orchestrator.generate_shot_image."""
    try:
        return await generate_shot_image(db, shot_id)
    except CharactersNotLockedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
