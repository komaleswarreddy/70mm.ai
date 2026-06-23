from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
from app.database import get_db
from app import models, schemas, ai_service

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/projects/{project_id}/generate-story")
async def generate_story(project_id: str, input_data: schemas.IdeaInput, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    story_data = await ai_service.generate_story_from_idea(input_data.idea)
    
    project.premise = story_data.get("premise", "")
    project.synopsis = story_data.get("synopsis", "")
    project.beat_sheet = json.dumps(story_data.get("beat_sheet", []))
    project.act_structure = json.dumps(story_data.get("act_structure", {}))
    project.themes = json.dumps(story_data.get("themes", []))
    project.conflicts = json.dumps(story_data.get("conflicts", {}))
    project.endings = json.dumps(story_data.get("endings", {}))

    
    # Clean old characters
    old_chars = await db.execute(select(models.Character).filter(models.Character.project_id == project_id))
    for char in old_chars.scalars().all():
        await db.delete(char)
        
    for char_data in story_data.get("characters", []):
        db_char = models.Character(
            project_id=project_id,
            name=char_data.get("name", "Unknown"),
            description=char_data.get("description", ""),
            traits=json.dumps(char_data.get("traits", [])),
            age=char_data.get("age"),
            personality=char_data.get("personality", ""),
            weakness=char_data.get("weakness", ""),
            motivation=char_data.get("motivation", ""),
            fear=char_data.get("fear", ""),
            backstory=char_data.get("backstory", ""),
            relationships=json.dumps(char_data.get("relationships", {}))
        )
        db.add(db_char)

        
    await db.commit()
    await db.refresh(project)
    return story_data

@router.post("/scenes/{scene_id}/formulate")
async def formulate_scene(scene_id: str, input_data: schemas.SceneFormulateInput, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Scene).filter(models.Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
        
    formulation = await ai_service.formulate_scene_ideas(input_data.action_line)
    return formulation

@router.post("/shots/{shot_id}/muse")
async def directors_muse(shot_id: str, input_data: schemas.DirectorMuseInput, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Shot).filter(models.Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    style = input_data.director_style or "Standard"
    muse_options = await ai_service.generate_directors_muse(input_data.action_line, style)
    
    # Insert history log
    db_history = models.DirectorMuseHistory(
        shot_id=shot_id,
        prompt=input_data.action_line,
        director_style=style,
        response=json.dumps(muse_options)
    )
    db.add(db_history)
    await db.commit()
    
    return muse_options


@router.post("/shots/{shot_id}/prompt-builder")
async def build_prompt(shot_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Shot).filter(models.Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    prompt_data = await ai_service.build_image_prompt(
        shot_size=shot.shot_size or "Medium Shot",
        lens=shot.lens or "50mm",
        emotion=shot.emotion or "Neutral",
        lighting=shot.lighting or "Natural",
        movement=shot.movement or "Static",
        action=shot.notes or "A character in a film scene."
    )
    return prompt_data
