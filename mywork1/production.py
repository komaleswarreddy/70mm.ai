from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import json
from datetime import datetime

from app.database import get_db
from app import models, schemas

router = APIRouter(tags=["production"])

# Project Versions
@router.post("/projects/{project_id}/versions", response_model=schemas.ProjectVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_project_version(project_id: str, payload: schemas.ProjectVersionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames),
            selectinload(models.Project.characters)
        )
        .filter(models.Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    snapshot_data = {
        "title": project.title,
        "logline": project.logline,
        "premise": project.premise,
        "synopsis": project.synopsis,
        "beat_sheet": project.beat_sheet,
        "act_structure": project.act_structure,
        "themes": project.themes,
        "conflicts": project.conflicts,
        "endings": project.endings,
        "characters": [
            {
                "name": c.name,
                "description": c.description,
                "traits": c.traits,
                "age": c.age,
                "personality": c.personality,
                "weakness": c.weakness,
                "motivation": c.motivation,
                "fear": c.fear,
                "backstory": c.backstory,
                "reference_image_url": c.reference_image_url,
                "relationships": c.relationships
            } for c in project.characters
        ],
        "scenes": [
            {
                "scene_number": s.scene_number,
                "heading": s.heading,
                "raw_content": s.raw_content,
                "parser_meta": s.parser_meta,
                "order": s.order,
                "action_blocks": [{"content": ab.content, "order": ab.order} for ab in s.action_blocks],
                "dialogues": [{"character_name": d.character_name, "content": d.content, "order": d.order} for d in s.dialogues],
                "shots": [
                    {
                        "shot_number": sh.shot_number,
                        "shot_size": sh.shot_size,
                        "angle": sh.angle,
                        "movement": sh.movement,
                        "lens": sh.lens,
                        "lighting": sh.lighting,
                        "emotion": sh.emotion,
                        "color_palette": sh.color_palette,
                        "visual_tip": sh.visual_tip,
                        "notes": sh.notes,
                        "order": sh.order,
                        "shooting_order": sh.shooting_order,
                        "location_order": sh.location_order,
                        "day_night": sh.day_night,
                        "duration": sh.duration,
                        "status": sh.status,
                        "color_label": sh.color_label,
                        "storyboard_frames": [
                            {
                                "image_url": f.image_url,
                                "prompt": f.prompt,
                                "negative_prompt": f.negative_prompt,
                                "status": f.status
                            } for f in sh.storyboard_frames
                        ]
                    } for sh in s.shots
                ]
            } for s in project.scenes
        ]
    }

    db_version = models.ProjectVersion(
        project_id=project_id,
        version_name=payload.version_name,
        snapshot=json.dumps(snapshot_data)
    )
    db.add(db_version)
    await db.commit()
    await db.refresh(db_version)
    return db_version

@router.get("/projects/{project_id}/versions", response_model=List[schemas.ProjectVersionResponse])
async def list_project_versions(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.ProjectVersion)
        .filter(models.ProjectVersion.project_id == project_id)
        .order_by(models.ProjectVersion.created_at.desc())
    )
    return result.scalars().all()

@router.post("/versions/{version_id}/restore")
async def restore_project_version(version_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ProjectVersion).filter(models.ProjectVersion.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version snapshot not found")

    proj_result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.scenes).selectinload(models.Scene.action_blocks),
            selectinload(models.Project.scenes).selectinload(models.Scene.dialogues),
            selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames),
            selectinload(models.Project.characters)
        )
        .filter(models.Project.id == version.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    snapshot = json.loads(version.snapshot)

    project.title = snapshot.get("title", project.title)
    project.logline = snapshot.get("logline", project.logline)
    project.premise = snapshot.get("premise", project.premise)
    project.synopsis = snapshot.get("synopsis", project.synopsis)
    project.beat_sheet = snapshot.get("beat_sheet", project.beat_sheet)
    project.act_structure = snapshot.get("act_structure", project.act_structure)
    project.themes = snapshot.get("themes", project.themes)
    project.conflicts = snapshot.get("conflicts", project.conflicts)
    project.endings = snapshot.get("endings", project.endings)

    for char in project.characters:
        await db.delete(char)
    for sc in project.scenes:
        await db.delete(sc)
    await db.flush()

    for char_data in snapshot.get("characters", []):
        db_char = models.Character(
            project_id=project.id,
            name=char_data["name"],
            description=char_data.get("description"),
            traits=char_data.get("traits"),
            age=char_data.get("age"),
            personality=char_data.get("personality"),
            weakness=char_data.get("weakness"),
            motivation=char_data.get("motivation"),
            fear=char_data.get("fear"),
            backstory=char_data.get("backstory"),
            reference_image_url=char_data.get("reference_image_url"),
            relationships=char_data.get("relationships")
        )
        db.add(db_char)

    for sc_data in snapshot.get("scenes", []):
        db_scene = models.Scene(
            project_id=project.id,
            scene_number=sc_data["scene_number"],
            heading=sc_data["heading"],
            raw_content=sc_data.get("raw_content"),
            parser_meta=sc_data.get("parser_meta"),
            order=sc_data.get("order", 0)
        )
        db.add(db_scene)
        await db.flush()

        for ab in sc_data.get("action_blocks", []):
            db.add(models.ActionBlock(scene_id=db_scene.id, content=ab["content"], order=ab.get("order", 0)))
        for dial in sc_data.get("dialogues", []):
            db.add(models.Dialogue(scene_id=db_scene.id, character_name=dial["character_name"], content=dial["content"], order=dial.get("order", 0)))
        for sh in sc_data.get("shots", []):
            db_shot = models.Shot(
                scene_id=db_scene.id,
                shot_number=sh["shot_number"],
                shot_size=sh.get("shot_size"),
                angle=sh.get("angle"),
                movement=sh.get("movement"),
                lens=sh.get("lens"),
                lighting=sh.get("lighting"),
                emotion=sh.get("emotion"),
                color_palette=sh.get("color_palette"),
                visual_tip=sh.get("visual_tip"),
                notes=sh.get("notes"),
                order=sh.get("order", 0),
                shooting_order=sh.get("shooting_order", 0),
                location_order=sh.get("location_order"),
                day_night=sh.get("day_night", "Day"),
                duration=sh.get("duration", 0),
                status=sh.get("status", "Pending"),
                color_label=sh.get("color_label")
            )
            db.add(db_shot)
            await db.flush()

            for f in sh.get("storyboard_frames", []):
                db.add(models.StoryboardFrame(
                    shot_id=db_shot.id,
                    image_url=f.get("image_url"),
                    prompt=f.get("prompt"),
                    negative_prompt=f.get("negative_prompt"),
                    status=f.get("status", "pending")
                ))

    await db.commit()
    return {"status": "success", "detail": "Project restored successfully"}

# Call Sheets
@router.post("/projects/{project_id}/callsheets", response_model=schemas.CallSheetResponse, status_code=status.HTTP_201_CREATED)
async def create_callsheet(project_id: str, callsheet: schemas.CallSheetCreate, db: AsyncSession = Depends(get_db)):
    db_cs = models.CallSheet(
        project_id=project_id,
        date=callsheet.date,
        call_time=callsheet.call_time,
        location=callsheet.location,
        notes=callsheet.notes
    )
    db.add(db_cs)
    await db.commit()
    await db.refresh(db_cs)
    return db_cs

@router.get("/projects/{project_id}/callsheets", response_model=List[schemas.CallSheetResponse])
async def list_callsheets(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.CallSheet)
        .filter(models.CallSheet.project_id == project_id)
        .order_by(models.CallSheet.created_at.desc())
    )
    return result.scalars().all()

@router.delete("/callsheets/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_callsheet(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.CallSheet).filter(models.CallSheet.id == id))
    cs = result.scalar_one_or_none()
    if not cs:
        raise HTTPException(status_code=404, detail="Call sheet not found")
    await db.delete(cs)
    await db.commit()
    return None

# Budget Items
@router.post("/projects/{project_id}/budget", response_model=schemas.BudgetItemResponse, status_code=status.HTTP_201_CREATED)
async def create_budget_item(project_id: str, item: schemas.BudgetItemCreate, db: AsyncSession = Depends(get_db)):
    db_item = models.BudgetItem(
        project_id=project_id,
        category=item.category,
        name=item.name,
        cost=item.cost
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.get("/projects/{project_id}/budget", response_model=List[schemas.BudgetItemResponse])
async def list_budget_items(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.BudgetItem)
        .filter(models.BudgetItem.project_id == project_id)
    )
    return result.scalars().all()

@router.delete("/budget/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget_item(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.BudgetItem).filter(models.BudgetItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    await db.delete(item)
    await db.commit()
    return None

# Collaborator Comments
@router.post("/projects/{project_id}/comments", response_model=schemas.CollaboratorCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(project_id: str, comment: schemas.CollaboratorCommentCreate, db: AsyncSession = Depends(get_db)):
    db_comment = models.CollaboratorComment(
        project_id=project_id,
        scene_id=comment.scene_id,
        user_name=comment.user_name,
        role=comment.role,
        content=comment.content
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

@router.get("/projects/{project_id}/comments", response_model=List[schemas.CollaboratorCommentResponse])
async def list_comments(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.CollaboratorComment)
        .filter(models.CollaboratorComment.project_id == project_id)
        .order_by(models.CollaboratorComment.created_at.asc())
    )
    return result.scalars().all()

@router.delete("/comments/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.CollaboratorComment).filter(models.CollaboratorComment.id == id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(comment)
    await db.commit()
    return None
