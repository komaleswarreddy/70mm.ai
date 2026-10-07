import asyncio
import json
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from io import BytesIO
from app.database import get_db
from app import models, schemas, ai_service
from app.parser import parse_screenplay, structure_scenes
from app.export_service import generate_project_pdf, generate_project_csv
from app.auth_service import get_current_user
from app import board_service
from app.shot_prompt_builder import resolve_wardrobe

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
    await db.refresh(dup_project)  # ensure id is populated in async context
    dup_project_id = str(dup_project.id)  # capture while object is alive
    
    for char in project.characters:
        dup_char = models.Character(
            project_id=dup_project_id,
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
            project_id=dup_project_id,
            scene_number=scene.scene_number,
            heading=scene.heading,
            raw_content=scene.raw_content,
            parser_meta=scene.parser_meta,
            order=scene.order
        )
        db.add(dup_scene)
        await db.flush()
        await db.refresh(dup_scene)
        dup_scene_id = str(dup_scene.id)
        
        for block in scene.action_blocks:
            dup_block = models.ActionBlock(
                scene_id=dup_scene_id,
                content=block.content,
                order=block.order
            )
            db.add(dup_block)
            
        for dial in scene.dialogues:
            dup_dial = models.Dialogue(
                scene_id=dup_scene_id,
                character_name=dial.character_name,
                content=dial.content,
                order=dial.order
            )
            db.add(dup_dial)
            
        for shot in scene.shots:
            dup_shot = models.Shot(
                scene_id=dup_scene_id,
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
            await db.refresh(dup_shot)
            dup_shot_id = str(dup_shot.id)
            
            for frame in shot.storyboard_frames:
                dup_frame = models.StoryboardFrame(
                    shot_id=dup_shot_id,
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
        .filter(models.Project.id == dup_project_id)
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
    structured_scenes = {s["scene_number"]: s for s in structure_scenes(parsed)}

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
        stage1 = structured_scenes.get(scene_data["scene_number"], {})
        db_scene = models.Scene(
            project_id=id,
            scene_number=scene_data["scene_number"],
            heading=scene_data["heading"],
            order=s_idx,
            raw_content="",
            int_ext=stage1.get("int_ext"),
            location=stage1.get("location"),
            time_of_day=stage1.get("time_of_day"),
            raw_action=stage1.get("raw_action"),
            raw_dialogue=json.dumps(stage1.get("raw_dialogue", [])),
            characters_present=json.dumps(stage1.get("characters_present", [])),
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

@router.post("/{id}/structure", response_model=schemas.ProjectResponse)
async def structure_project(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Stage 2: Acts -> Sequences -> Beats. Requires Stage 1 (parse) to have
    run first — operates on the already-parsed scene list, never raw text."""
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.scenes))
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.scenes:
        raise HTTPException(status_code=400, detail="No scenes found — run Stage 1 (/parse) on this project first.")

    scenes_payload = [
        {
            "scene_number": s.scene_number,
            "heading": s.heading,
            "raw_action": s.raw_action,
            "characters_present": json.loads(s.characters_present) if s.characters_present else [],
        }
        for s in project.scenes
    ]

    structure = await ai_service.structure_screenplay(scenes_payload)
    project.screenplay_structure = json.dumps(structure)
    await db.commit()

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

@router.post("/{id}/boards/compose", response_model=List[schemas.BoardResponse])
async def compose_boards(id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Stage 8: compose the production board sheets (PNG 7200 px + vector PDF
    with full-resolution shots) from the Stage 7 images already generated.
    Board text comes from Project.board_legend_settings; missing shot captions
    are drafted once with the LLM and saved so they stay stable and editable.
    Replaces any previously composed boards."""
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.scenes).selectinload(models.Scene.shots).selectinload(models.Shot.storyboard_frames),
                 selectinload(models.Project.characters))
        .filter(models.Project.id == id, models.Project.user_id == current_user["uid"], models.Project.is_deleted == 0)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.scenes:
        raise HTTPException(status_code=400, detail="No scenes found — run Stage 1 (/parse) on this project first.")

    backend_root = board_service.BACKEND_ROOT
    settings = json.loads(project.board_legend_settings) if project.board_legend_settings else {}
    if not isinstance(settings, dict):
        settings = {}

    scenes = sorted(project.scenes, key=lambda s: s.scene_number)
    # Draft captions for shots that have none, once, and persist them.
    for scene in scenes:
        missing = [s for s in scene.shots if not (s.board_caption or "").strip()]
        if not missing:
            continue
        drafts = await ai_service.draft_board_captions(
            scene.heading or "", scene.raw_content or scene.raw_action or "",
            [{"shot_number": s.shot_number, "shot_size": s.shot_size, "reasoning": s.reasoning, "notes": s.notes} for s in missing],
        )
        for s in missing:
            draft = drafts.get(s.shot_number) or {}
            s.board_caption = draft.get("caption") or (s.reasoning or "").split(".")[0][:90] or None
            if draft.get("dialogue") and not s.board_dialogue:
                s.board_dialogue = draft["dialogue"]

    project_payload = {
        "title": project.title, "period": project.period,
        "characters": [], "scenes": [],
    }
    for c in sorted(project.characters, key=lambda c: c.name):
        refs = [p for p in (json.loads(c.reference_image_paths) if c.reference_image_paths else [])]
        disk = [os.path.join(backend_root, p.lstrip("/")) for p in refs]
        disk = [p for p in disk if os.path.exists(p)]
        if c.is_locked and disk:
            project_payload["characters"].append({"name": c.name, "ref_paths": disk,
                                                  "note": resolve_wardrobe(c.wardrobe, None)[:48]})
    for scene in scenes:
        shots_payload = []
        for shot in sorted(scene.shots, key=lambda s: (s.order or 0, s.shot_number)):
            frame = next((f for f in shot.storyboard_frames if f.status == "completed" and f.image_url), None)
            image_path = os.path.join(backend_root, frame.image_url.lstrip("/")) if frame else None
            try:
                crop = json.loads(shot.board_crop) if shot.board_crop else None
            except ValueError:
                crop = None
            shots_payload.append({
                "shot_number": shot.shot_number, "shot_size": shot.shot_size or shot.shot_type, "lens": shot.lens,
                "movement": shot.movement, "lighting": shot.lighting, "emotion": shot.emotion,
                "color_palette": shot.color_palette, "caption": shot.board_caption, "dialogue": shot.board_dialogue,
                "crop": crop, "image_path": image_path,
            })
        project_payload["scenes"].append({"scene_number": scene.scene_number, "heading": scene.heading, "shots": shots_payload})

    # Rendering is CPU-bound (~10-15 s for a full sheet); keep the event loop free.
    # Unchanged inputs return the previous files instantly (fingerprint cache).
    await db.commit()  # persist any newly drafted captions before the long step
    rendered, cached = await asyncio.to_thread(
        board_service.compose_project_boards, project_payload, settings, id
    )

    existing = (await db.execute(
        select(models.Board).filter(models.Board.project_id == id).order_by(models.Board.board_number)
    )).scalars().all()
    if cached and len(existing) == len(rendered) and all(
            b.output_pdf_path == f"/static/boards/{os.path.basename(r['pdf_path'])}" for b, r in zip(existing, rendered)):
        return existing   # same files, same rows -> browser caches stay valid
    for old_board in existing:
        await db.delete(old_board)
    await db.flush()

    new_boards = []
    for b in rendered:
        start, end = b["scene_range"]
        db_board = models.Board(
            project_id=id, board_number=b["board_number"], scene_range_start=start, scene_range_end=end,
            title=f"Scenes {start}-{end}" if start != end else f"Scene {start}",
            length_label=f"{b['shot_count']} shots", page_range_label=f"{b['board_number']} OF {b['total']}",
            output_image_path=f"/static/boards/{os.path.basename(b['png_path'])}",
            output_pdf_path=f"/static/boards/{os.path.basename(b['pdf_path'])}",
        )
        db.add(db_board)
        new_boards.append(db_board)

    await db.commit()
    for b in new_boards:
        await db.refresh(b)
    return new_boards

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
