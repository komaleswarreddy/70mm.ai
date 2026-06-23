from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app import models, schemas

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

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Character).filter(models.Character.id == id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    await db.delete(character)
    await db.commit()
    return None
