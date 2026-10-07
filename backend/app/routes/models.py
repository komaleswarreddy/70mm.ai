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

    # ── Storyboard & Cinematography Engine (Stage 2 + Stage 8) ────────────
    # NOTE: distinct from `act_structure`/`beat_sheet` above, which hold the
    # idea-to-story generator's output (act_1/act_2/act_3 prose + a flat beat
    # list). `screenplay_structure` holds Stage 2's Acts -> Sequences -> Beats
    # hierarchy derived from an already-parsed screenplay's real scene numbers.
    screenplay_structure = Column(Text, nullable=True)  # JSON: {"acts": [...]}
    # Board footer legend (camera style / color tone / lighting / mood / notes
    # / lens guide) — one project-level default, editable, shared by every
    # board on compose rather than recomputed per board.
    board_legend_settings = Column(Text, nullable=True)  # JSON
    # Era/setting stated in every image prompt, e.g. "India, 1965" -- without it
    # nothing tells the image model a period film is a period film.
    period = Column(String, nullable=True)

    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    boards = relationship("Board", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

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

    # ── Stage 1: deterministic parse (slugline breakdown) ─────────────────
    int_ext = Column(String, nullable=True)          # INT | EXT | INT/EXT
    location = Column(String, nullable=True)
    time_of_day = Column(String, nullable=True)       # DAY | NIGHT | CONTINUOUS | ...
    raw_action = Column(Text, nullable=True)          # joined action lines
    raw_dialogue = Column(Text, nullable=True)        # JSON: [{"character","content"}]
    characters_present = Column(Text, nullable=True)  # JSON list[str]

    # ── Stage 3: scene understanding ───────────────────────────────────────
    action_summary = Column(Text, nullable=True)
    emotion = Column(String, nullable=True)
    conflict = Column(Text, nullable=True)
    key_objects = Column(Text, nullable=True)         # JSON list[str]
    visual_emphasis = Column(Text, nullable=True)
    continuity_notes = Column(Text, nullable=True)    # JSON list[str]

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

    # ── Stage 6: character asset & consistency system ──────────────────────
    # `reference_image_url` above stays the single "primary" reference used
    # by existing UI; these hold the full locked bible without touching it.
    reference_image_paths = Column(Text, nullable=True)  # JSON list[str], 1-4 locked refs
    embedding_vector = Column(Text, nullable=True)        # JSON list[float] (CLIP embedding)
    locked_seed = Column(Integer, nullable=True)
    is_locked = Column(Integer, default=0)  # bool: bible finalized, safe to condition generation on
    # Costume continuity, kept apart from `description` (identity only: face,
    # body, hair) so a character can change clothes between scenes as the
    # script says. JSON: {"default": str, "by_scene": {"<scene_number>": str}}
    wardrobe = Column(Text, nullable=True)

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

    # ── Stage 4: automatic shot division ────────────────────────────────────
    # `shot_type` is the shot's fundamental kind (spec's canonical enum incl.
    # Two-Shot/OTS/POV/Insert/Cutaway, which `shot_size` alone can't express).
    # `reasoning` is required by the acceptance criteria — never left empty.
    shot_type = Column(String, nullable=True)
    reasoning = Column(Text, nullable=True)

    # ── Stage 5: cinematography plan (extra fields beyond the existing
    # shot_size/angle/movement/lens/lighting/emotion/color_palette above) ──
    camera_height = Column(String, nullable=True)
    framing = Column(Text, nullable=True)
    composition_notes = Column(Text, nullable=True)
    # Rich structured lighting {key, fill, backlight, practicals, quality,
    # direction, intensity, color_temp_k}. Kept separate from the existing
    # plain-string `lighting` column, which the frontend already renders.
    lighting_detail = Column(Text, nullable=True)  # JSON
    contrast = Column(String, nullable=True)          # Low | Medium | High
    depth_of_field = Column(String, nullable=True)    # Shallow | Deep
    perspective_notes = Column(Text, nullable=True)

    # ── Stage 7: image generation ───────────────────────────────────────────
    # Which named characters actually appear in THIS shot (a subset of the
    # scene's characters_present — e.g. one CU in a 2-character scene only
    # has one of them). Drives which characters' USO reference images get
    # pooled for this shot's generation.
    characters_in_shot = Column(Text, nullable=True)  # JSON list[str]

    # ── Stage 9: visual continuity QA ───────────────────────────────────────
    needs_review = Column(Integer, default=0)  # bool
    # ── Stage 8: production board sheet ────────────────────────────────────
    board_caption = Column(Text, nullable=True)   # one-line action caption under the panel
    board_dialogue = Column(Text, nullable=True)  # key dialogue line, e.g. SITA: "Do I know you?"
    board_crop = Column(Text, nullable=True)      # JSON [left, top, right, bottom] in source pixels -- a reframe, never baked into the image
    continuity_score = Column(Integer, nullable=True)  # cosine similarity * 1000, for debugging thresholds

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

class Board(Base):
    """Stage 8: a composited, numbered multi-panel board sheet covering a
    contiguous range of scenes (~5 scenes/board) — the printable PNG/PDF a
    1st AD or DP would actually be handed, not a single shot's image."""
    __tablename__ = "boards"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    board_number = Column(Integer, nullable=False)
    scene_range_start = Column(Integer, nullable=False)
    scene_range_end = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    length_label = Column(String, nullable=True)      # e.g. "~22-24 MINS (PORTION)"
    page_range_label = Column(String, nullable=True)  # e.g. "1 OF 4"
    output_image_path = Column(String, nullable=True)
    output_pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="boards")

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
