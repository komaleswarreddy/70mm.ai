import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=True) # Linked Firebase Auth user ID
    title = Column(String, nullable=False)
    logline = Column(Text, nullable=True)
    premise = Column(Text, nullable=True)
    synopsis = Column(Text, nullable=True)
    beat_sheet = Column(Text, nullable=True)  # JSON String representation
    act_structure = Column(Text, nullable=True)  # JSON String representation
    themes = Column(Text, nullable=True)  # JSON String representation
    conflicts = Column(Text, nullable=True)  # JSON String representation
    endings = Column(Text, nullable=True)  # JSON String representation

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Integer, default=0)

    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    scene_number = Column(Integer, nullable=False)
    heading = Column(String, nullable=False)
    raw_content = Column(Text, nullable=True)
    parser_meta = Column(Text, nullable=True)  # JSON String
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scenes")
    action_blocks = relationship("ActionBlock", back_populates="scene", cascade="all, delete-orphan", lazy="selectin")
    dialogues = relationship("Dialogue", back_populates="scene", cascade="all, delete-orphan", lazy="selectin")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan", lazy="selectin")

class ActionBlock(Base):
    __tablename__ = "action_blocks"

    id = Column(String, primary_key=True, default=generate_uuid)
    scene_id = Column(String, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    order = Column(Integer, default=0)

    scene = relationship("Scene", back_populates="action_blocks")

class Dialogue(Base):
    __tablename__ = "dialogues"

    id = Column(String, primary_key=True, default=generate_uuid)
    scene_id = Column(String, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    character_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    order = Column(Integer, default=0)

    scene = relationship("Scene", back_populates="dialogues")

class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    traits = Column(Text, nullable=True)  # JSON String list
    age = Column(Integer, nullable=True)
    personality = Column(Text, nullable=True)
    weakness = Column(Text, nullable=True)
    motivation = Column(Text, nullable=True)
    fear = Column(Text, nullable=True)
    backstory = Column(Text, nullable=True)
    reference_image_url = Column(String, nullable=True)
    relationships = Column(Text, nullable=True)  # JSON structure: {"character_id": "type"}

    project = relationship("Project", back_populates="characters")

class DirectorMuseHistory(Base):
    __tablename__ = "director_muse_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    shot_id = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    director_style = Column(String, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Shot(Base):
    __tablename__ = "shots"

    id = Column(String, primary_key=True, default=generate_uuid)
    scene_id = Column(String, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    shot_number = Column(Integer, nullable=False)
    shot_size = Column(String, nullable=True)      # WS, MS, CU, etc.
    angle = Column(String, nullable=True)          # High, Low, Eye Level, etc.
    movement = Column(String, nullable=True)       # Pan, Tilt, Dolly, Static
    lens = Column(String, nullable=True)           # Wide, Telephoto, 50mm, etc.
    lighting = Column(String, nullable=True)       # High key, Low key, Dramatic, etc.
    emotion = Column(String, nullable=True)
    color_palette = Column(String, nullable=True)
    visual_tip = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    
    shooting_order = Column(Integer, default=0)
    location_order = Column(String, nullable=True)
    day_night = Column(String, default="Day")
    duration = Column(Integer, default=0)
    status = Column(String, default="Pending")
    color_label = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scene = relationship("Scene", back_populates="shots")
    storyboard_frames = relationship("StoryboardFrame", back_populates="shot", cascade="all, delete-orphan", lazy="selectin")

class StoryboardFrame(Base):
    __tablename__ = "storyboard_frames"

    id = Column(String, primary_key=True, default=generate_uuid)
    shot_id = Column(String, ForeignKey("shots.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=True)
    prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    shot = relationship("Shot", back_populates="storyboard_frames")

class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_name = Column(String, nullable=False)
    snapshot = Column(Text, nullable=False)  # JSON string snapshot
    created_at = Column(DateTime, default=datetime.utcnow)

class CallSheet(Base):
    __tablename__ = "call_sheets"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    date = Column(String, nullable=False)
    call_time = Column(String, default="08:00 AM")
    location = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False) # Cast, Crew, Props, Food, Equipment
    name = Column(String, nullable=False)
    cost = Column(Integer, default=0)

class CollaboratorComment(Base):
    __tablename__ = "collaborator_comments"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    scene_id = Column(String, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True)
    user_name = Column(String, nullable=False)
    role = Column(String, default="Writer")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
