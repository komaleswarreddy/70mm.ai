from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/projects")
async def search_projects(query: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Project)
        .filter(models.Project.title.ilike(f"%{query}%") | models.Project.logline.ilike(f"%{query}%"))
    )
    projects = result.scalars().all()
    return [{"id": p.id, "title": p.title, "logline": p.logline} for p in projects]

@router.get("/scenes")
async def search_scenes(query: str = Query(...), db: AsyncSession = Depends(get_db)):
    # Match headings or contents
    result = await db.execute(
        select(models.Scene)
        .options(selectinload(models.Scene.project))
        .filter(
            models.Scene.heading.ilike(f"%{query}%") | 
            models.Scene.raw_content.ilike(f"%{query}%")
        )
    )
    scenes = result.scalars().all()
    return [{
        "id": s.id,
        "project_id": s.project_id,
        "project_title": s.project.title if s.project else "Unknown",
        "scene_number": s.scene_number,
        "heading": s.heading,
        "raw_content": s.raw_content[:200] if s.raw_content else ""
    } for s in scenes]

@router.get("/shots")
async def search_shots(query: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Shot)
        .options(selectinload(models.Shot.scene).selectinload(models.Scene.project))
        .filter(
            models.Shot.notes.ilike(f"%{query}%") |
            models.Shot.lens.ilike(f"%{query}%") |
            models.Shot.lighting.ilike(f"%{query}%")
        )
    )
    shots = result.scalars().all()
    return [{
        "id": s.id,
        "shot_number": s.shot_number,
        "scene_id": s.scene_id,
        "scene_heading": s.scene.heading if s.scene else "Unknown",
        "project_title": s.scene.project.title if s.scene and s.scene.project else "Unknown",
        "notes": s.notes,
        "lens": s.lens,
        "lighting": s.lighting
    } for s in shots]
