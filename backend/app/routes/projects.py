import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from io import BytesIO
from app.database import get_db
from app import models, schemas
from app.parser import parse_screenplay
from app.export_service import generate_project_pdf, generate_project_csv
from app.auth_service import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: schemas.ProjectCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_project = models.Project(
        user_id=current_user["uid"],
        title=project.title,
        logline=project.logline,
        premise=project.premise,
        synopsis=project.synopsis,
        beat_sheet=project.beat_sheet,
        act_structure=project.act_structure,
        themes=project.themes,
        conflicts=project.conflicts,
        endings=project.endings
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.scenes), selectinload(models.Project.characters))
        .filter(models.Project.id == db_project.id)
    )
    return result.scalar_one()


@router.get("/", response_model=List[schemas.ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.scenes), selectinload(models.Project.characters))
        .filter(models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
        .offset(skip)
        .limit(limit)
        .order_by(models.Project.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{id}", response_model=schemas.ProjectResponse)
async def get_project(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"])
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.is_deleted = 1
    await db.commit()
    return None

@router.put("/{id}", response_model=schemas.ProjectResponse)
async def update_project(id: str, project_update: schemas.ProjectUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
        
    await db.commit()
    await db.refresh(project)
    return project

@router.post("/{id}/duplicate", response_model=schemas.ProjectResponse)
async def duplicate_project(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # 1. Fetch original project
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # 2. Create duplicate
    dup_project = models.Project(
        user_id=current_user["uid"],
        title=f"{project.title} (Copy)",
        logline=project.logline,
        premise=project.premise,
        synopsis=project.synopsis,
        beat_sheet=project.beat_sheet,
        act_structure=project.act_structure,
        themes=project.themes,
        conflicts=project.conflicts,
        endings=project.endings
    )

    db.add(dup_project)
    await db.flush()
    
    # 3. Duplicate characters
    for char in project.characters:
        dup_char = models.Character(
            project_id=dup_project.id,
            name=char.name,
            description=char.description,
            traits=char.traits,
            age=char.age,
            personality=char.personality,
            weakness=char.weakness,
            motivation=char.motivation,
            fear=char.fear,
            backstory=char.backstory,
            reference_image_url=char.reference_image_url,
            relationships=char.relationships
        )
        db.add(dup_char)

        
    # 4. Duplicate scenes, action blocks, dialogues, shots, and storyboards
    for scene in project.scenes:
        dup_scene = models.Scene(
            project_id=dup_project.id,
            scene_number=scene.scene_number,
            heading=scene.heading,
            raw_content=scene.raw_content,
            parser_meta=scene.parser_meta,
            order=scene.order
        )
        db.add(dup_scene)
        await db.flush()
        
        for block in scene.action_blocks:
            dup_block = models.ActionBlock(
                scene_id=dup_scene.id,
                content=block.content,
                order=block.order
            )
            db.add(dup_block)
            
        for dial in scene.dialogues:
            dup_dial = models.Dialogue(
                scene_id=dup_scene.id,
                character_name=dial.character_name,
                content=dial.content,
                order=dial.order
            )
            db.add(dup_dial)
            
        for shot in scene.shots:
            dup_shot = models.Shot(
                scene_id=dup_scene.id,
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
                order=shot.order
            )
            db.add(dup_shot)
            await db.flush()
            
            for frame in shot.storyboard_frames:
                dup_frame = models.StoryboardFrame(
                    shot_id=dup_shot.id,
                    image_url=frame.image_url,
                    prompt=frame.prompt,
                    negative_prompt=frame.negative_prompt,
                    status=frame.status
                )
                db.add(dup_frame)
                
    await db.commit()
    
    reload_result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == dup_project.id)
    )
    return reload_result.scalar_one()

@router.post("/{id}/parse", response_model=schemas.ProjectResponse)
async def parse_script(id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    content_bytes = await file.read()
    try:
        from app.universal_importer import extract_text
        content = extract_text(file.filename, content_bytes)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
            
    parsed = parse_screenplay(content)
    
    # Cascade delete old scenes & characters
    old_scenes = await db.execute(select(models.Scene).filter(models.Scene.project_id == id))
    for scene in old_scenes.scalars().all():
        await db.delete(scene)
        
    old_chars = await db.execute(select(models.Character).filter(models.Character.project_id == id))
    for char in old_chars.scalars().all():
        await db.delete(char)
        
    # Insert characters
    for char_name in parsed["characters"]:
        db_char = models.Character(
            project_id=id,
            name=char_name,
            traits=json.dumps([])
        )
        db.add(db_char)
        
    # Insert scenes
    for s_idx, scene_data in enumerate(parsed["scenes"]):
        db_scene = models.Scene(
            project_id=id,
            scene_number=scene_data["scene_number"],
            heading=scene_data["heading"],
            order=s_idx,
            raw_content=""
        )
        db.add(db_scene)
        await db.flush()
        
        raw_elements = []
        action_order = 0
        dialogue_order = 0
        
        for elem in scene_data["elements"]:
            if elem["type"] == "action":
                db_action = models.ActionBlock(
                    scene_id=db_scene.id,
                    content=elem["content"],
                    order=action_order
                )
                db.add(db_action)
                action_order += 1
                raw_elements.append(f"{elem['content']}\n")
            elif elem["type"] == "dialogue":
                db_dialogue = models.Dialogue(
                    scene_id=db_scene.id,
                    character_name=elem["character"],
                    content=elem["content"],
                    order=dialogue_order
                )
                db.add(db_dialogue)
                dialogue_order += 1
                raw_elements.append(f"{elem['character']}\n{elem['content']}\n")
                
        db_scene.raw_content = "\n".join(raw_elements)
        
    await db.commit()
    
    # Reload project
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"])
    )
    return result.scalar_one()

@router.get("/{id}/export/pdf")
async def export_pdf(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.characters),
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"])
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    pdf_bytes = generate_project_pdf(project)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=project_{id}_export.pdf"}
    )

@router.get("/{id}/export/csv")
async def export_csv(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.scenes).selectinload(models.Scene.shots)
        )
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"])
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    csv_str = generate_project_csv(project)
    return StreamingResponse(
        BytesIO(csv_str.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=project_{id}_export.csv"}
    )
