import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.shot_prompt_builder import resolve_wardrobe
from app.character_asset_service import lock_character_reference

router = APIRouter(prefix="/characters", tags=["characters"])

@router.get("/", response_model=List[schemas.CharacterResponse])
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Character)
        .filter(models.Character.project_id == project_id)
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(project_id: str, character: schemas.CharacterCreate, db: AsyncSession = Depends(get_db)):
    # Verify project exists
    proj_result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_char = models.Character(
        project_id=project_id,
        name=character.name,
        description=character.description,
        traits=character.traits,
        age=character.age,
        personality=character.personality,
        weakness=character.weakness,
        motivation=character.motivation,
        fear=character.fear,
        backstory=character.backstory,
        reference_image_url=character.reference_image_url,
        relationships=character.relationships
    )
    db.add(db_char)
    await db.commit()
    await db.refresh(db_char)
    return db_char

@router.get("/{id}", response_model=schemas.CharacterResponse)
async def get_character(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Character).filter(models.Character.id == id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

@router.put("/{id}", response_model=schemas.CharacterResponse)
async def update_character(id: str, character_update: schemas.CharacterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Character).filter(models.Character.id == id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
        
    update_data = character_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
        
    await db.commit()
    await db.refresh(character)
    return character

@router.post("/{id}/lock-reference", response_model=schemas.CharacterResponse)
async def lock_reference(
    id: str,
    # Four named optional single-file params, not List[UploadFile] --
    # verified live (and confirmed as a known upstream bug, fixed in
    # fastapi>=0.113.0) that THIS installed fastapi/starlette/pydantic
    # combination (0.111.0/0.37.2/2.7.4) fails multipart validation with
    # "Input should be a valid list" for a List[UploadFile] field
    # regardless of file count (reproduced with both 1 and 4 files) or
    # default value (None vs []). Four explicit params sidesteps that
    # buggy code path entirely, and the route already caps at 4 files.
    file1: Optional[UploadFile] = File(None),
    file2: Optional[UploadFile] = File(None),
    file3: Optional[UploadFile] = File(None),
    file4: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Stage 6: builds and locks this character's reference bible. Pass 1-4
    image files to lock user-supplied/consented references; pass none to
    auto-generate one reference with a fresh seed and freeze that seed.
    Every subsequent shot containing this character must condition on the
    locked references — see character_consistency.py, which refuses to
    generate for an unlocked character.
    """
    result = await db.execute(select(models.Character).filter(models.Character.id == id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    files = [f for f in (file1, file2, file3, file4) if f is not None]
    uploaded_images = None
    if files:
        uploaded_images = [await f.read() for f in files]

    period = (await db.execute(
        select(models.Project.period).filter(models.Project.id == character.project_id)
    )).scalar_one_or_none()
    locked = await lock_character_reference(
        character_id=character.id,
        character_name=character.name,
        character_description=character.description,
        uploaded_images=uploaded_images,
        wardrobe=resolve_wardrobe(character.wardrobe, None),
        period=period or "",
    )

    character.reference_image_paths = json.dumps(locked["reference_image_paths"])
    character.reference_image_url = locked["reference_image_paths"][0]  # primary ref for existing UI
    character.embedding_vector = json.dumps(locked["embedding_vector"]) if locked["embedding_vector"] else None
    character.locked_seed = locked["locked_seed"]
    character.is_locked = 1

    await db.commit()
    await db.refresh(character)
    return character

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Character).filter(models.Character.id == id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    await db.delete(character)
    await db.commit()
    return None
