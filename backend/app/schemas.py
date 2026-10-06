from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class StoryboardFrameBase(BaseModel):
    shot_id: str
    image_url: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    status: str = "pending"

class StoryboardFrameCreate(StoryboardFrameBase):
    pass

class StoryboardFrameResponse(StoryboardFrameBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ShotBase(BaseModel):
    shot_number: int
    shot_size: Optional[str] = None
    angle: Optional[str] = None
    movement: Optional[str] = None
    lens: Optional[str] = None
    lighting: Optional[str] = None
    emotion: Optional[str] = None
    color_palette: Optional[str] = None
    visual_tip: Optional[str] = None
    notes: Optional[str] = None
    order: Optional[int] = 0
    shooting_order: Optional[int] = 0
    location_order: Optional[str] = None
    day_night: Optional[str] = "Day"
    duration: Optional[int] = 0
    status: Optional[str] = "Pending"
    color_label: Optional[str] = None
    # Stage 4 — automatic shot division
    shot_type: Optional[str] = None
    reasoning: Optional[str] = None
    # Stage 5 — cinematography plan (extra fields)
    camera_height: Optional[str] = None
    framing: Optional[str] = None
    composition_notes: Optional[str] = None
    lighting_detail: Optional[str] = None  # JSON string
    contrast: Optional[str] = None
    depth_of_field: Optional[str] = None
    perspective_notes: Optional[str] = None
    # Stage 7 — image generation
    characters_in_shot: Optional[str] = None
    board_caption: Optional[str] = None
    board_dialogue: Optional[str] = None
    board_crop: Optional[str] = None  # JSON [l, t, r, b]  # JSON string list[str]
    # Stage 9 — continuity QA
    needs_review: Optional[int] = 0
    continuity_score: Optional[int] = None

class ShotCreate(ShotBase):
    pass

class ShotUpdate(BaseModel):
    shot_number: Optional[int] = None
    shot_size: Optional[str] = None
    angle: Optional[str] = None
    movement: Optional[str] = None
    lens: Optional[str] = None
    lighting: Optional[str] = None
    emotion: Optional[str] = None
    color_palette: Optional[str] = None
    visual_tip: Optional[str] = None
    notes: Optional[str] = None
    order: Optional[int] = None
    shooting_order: Optional[int] = None
    location_order: Optional[str] = None
    day_night: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    color_label: Optional[str] = None
    shot_type: Optional[str] = None
    reasoning: Optional[str] = None
    camera_height: Optional[str] = None
    framing: Optional[str] = None
    composition_notes: Optional[str] = None
    lighting_detail: Optional[str] = None
    contrast: Optional[str] = None
    depth_of_field: Optional[str] = None
    perspective_notes: Optional[str] = None
    characters_in_shot: Optional[str] = None
    board_caption: Optional[str] = None
    board_dialogue: Optional[str] = None
    board_crop: Optional[str] = None  # JSON [l, t, r, b]
    needs_review: Optional[int] = None
    continuity_score: Optional[int] = None

class ShotResponse(ShotBase):
    id: str
    scene_id: str
    created_at: datetime
    updated_at: datetime
    storyboard_frames: List[StoryboardFrameResponse] = []
    model_config = ConfigDict(from_attributes=True)

class ActionBlockResponse(BaseModel):
    id: str
    scene_id: str
    content: str
    order: int
    model_config = ConfigDict(from_attributes=True)

class DialogueResponse(BaseModel):
    id: str
    scene_id: str
    character_name: str
    content: str
    order: int
    model_config = ConfigDict(from_attributes=True)

class SceneBase(BaseModel):
    scene_number: int
    heading: str
    raw_content: Optional[str] = None
    parser_meta: Optional[str] = None
    order: Optional[int] = 0

class SceneCreate(SceneBase):
    pass

class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    heading: Optional[str] = None
    raw_content: Optional[str] = None
    parser_meta: Optional[str] = None
    order: Optional[int] = None
    # Stage 1 fields — editable in case the deterministic parse misreads an
    # unusually formatted slugline and a human needs to correct it.
    int_ext: Optional[str] = None
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    raw_action: Optional[str] = None
    raw_dialogue: Optional[str] = None            # JSON string
    characters_present: Optional[str] = None      # JSON string
    # Stage 3 fields
    action_summary: Optional[str] = None
    emotion: Optional[str] = None
    conflict: Optional[str] = None
    key_objects: Optional[str] = None             # JSON string
    visual_emphasis: Optional[str] = None
    continuity_notes: Optional[str] = None        # JSON string

class SceneResponse(SceneBase):
    id: str
    project_id: str
    created_at: datetime
    int_ext: Optional[str] = None
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    raw_action: Optional[str] = None
    raw_dialogue: Optional[str] = None
    characters_present: Optional[str] = None
    action_summary: Optional[str] = None
    emotion: Optional[str] = None
    conflict: Optional[str] = None
    key_objects: Optional[str] = None
    visual_emphasis: Optional[str] = None
    continuity_notes: Optional[str] = None
    action_blocks: List[ActionBlockResponse] = []
    dialogues: List[DialogueResponse] = []
    shots: List[ShotResponse] = []
    model_config = ConfigDict(from_attributes=True)

class CharacterBase(BaseModel):
    name: str
    description: Optional[str] = None
    traits: Optional[str] = None # JSON string list
    age: Optional[int] = None
    personality: Optional[str] = None
    weakness: Optional[str] = None
    motivation: Optional[str] = None
    fear: Optional[str] = None
    backstory: Optional[str] = None
    reference_image_url: Optional[str] = None
    relationships: Optional[str] = None # JSON string: {"character_id": "type"}
    wardrobe: Optional[str] = None # JSON string: {"default": str, "by_scene": {"<scene_number>": str}}

class CharacterCreate(CharacterBase):
    pass

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    traits: Optional[str] = None
    age: Optional[int] = None
    personality: Optional[str] = None
    weakness: Optional[str] = None
    motivation: Optional[str] = None
    fear: Optional[str] = None
    backstory: Optional[str] = None
    reference_image_url: Optional[str] = None
    relationships: Optional[str] = None
    wardrobe: Optional[str] = None
    reference_image_paths: Optional[str] = None  # JSON string list
    embedding_vector: Optional[str] = None        # JSON string list[float]
    locked_seed: Optional[int] = None
    is_locked: Optional[int] = None

class CharacterResponse(CharacterBase):
    id: str
    project_id: str
    reference_image_paths: Optional[str] = None
    embedding_vector: Optional[str] = None
    locked_seed: Optional[int] = None
    is_locked: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)

class DirectorMuseHistoryResponse(BaseModel):
    id: str
    shot_id: str
    prompt: str
    director_style: str
    response: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str
    user_id: Optional[str] = None
    logline: Optional[str] = None
    premise: Optional[str] = None
    synopsis: Optional[str] = None
    beat_sheet: Optional[str] = None # JSON String
    act_structure: Optional[str] = None # JSON String
    themes: Optional[str] = None # JSON String
    conflicts: Optional[str] = None # JSON String
    endings: Optional[str] = None # JSON String
    period: Optional[str] = None  # e.g. "India, 1965" -- stated in every image prompt
    is_deleted: Optional[int] = 0

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    logline: Optional[str] = None
    premise: Optional[str] = None
    synopsis: Optional[str] = None
    beat_sheet: Optional[str] = None
    act_structure: Optional[str] = None
    themes: Optional[str] = None
    conflicts: Optional[str] = None
    endings: Optional[str] = None
    period: Optional[str] = None
    screenplay_structure: Optional[str] = None    # JSON string — Stage 2 Acts/Sequences/Beats
    board_legend_settings: Optional[str] = None   # JSON string — Stage 8 footer legend defaults


class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime
    screenplay_structure: Optional[str] = None
    board_legend_settings: Optional[str] = None
    scenes: List[SceneResponse] = []
    characters: List[CharacterResponse] = []
    model_config = ConfigDict(from_attributes=True)

class BoardBase(BaseModel):
    board_number: int
    scene_range_start: int
    scene_range_end: int
    title: Optional[str] = None
    length_label: Optional[str] = None
    page_range_label: Optional[str] = None
    output_image_path: Optional[str] = None
    output_pdf_path: Optional[str] = None

class BoardResponse(BoardBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ContinuityCheckResponse(BaseModel):
    shot_id: str
    needs_review: bool
    flags: List[str]
    identity_score: Optional[float] = None
    color_distance: Optional[float] = None
    regenerated: bool = False

class ReorderRequest(BaseModel):
    ids: List[str]

class IdeaInput(BaseModel):
    idea: str

class SceneFormulateInput(BaseModel):
    action_line: str

class DirectorMuseInput(BaseModel):
    action_line: str
    director_style: Optional[str] = "Standard"

class ShotEditInput(BaseModel):
    instruction: str

class ShotBatchUpdate(BaseModel):
    ids: List[str]
    updates: ShotUpdate

class ProjectVersionCreate(BaseModel):
    version_name: str

class ProjectVersionResponse(BaseModel):
    id: str
    project_id: str
    version_name: str
    snapshot: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CallSheetBase(BaseModel):
    date: str
    call_time: Optional[str] = "08:00 AM"
    location: Optional[str] = None
    notes: Optional[str] = None

class CallSheetCreate(CallSheetBase):
    pass

class CallSheetResponse(CallSheetBase):
    id: str
    project_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BudgetItemBase(BaseModel):
    category: str
    name: str
    cost: int = 0

class BudgetItemCreate(BudgetItemBase):
    pass

class BudgetItemResponse(BudgetItemBase):
    id: str
    project_id: str
    model_config = ConfigDict(from_attributes=True)

class CollaboratorCommentBase(BaseModel):
    scene_id: Optional[str] = None
    user_name: str
    role: Optional[str] = "Writer"
    content: str

class CollaboratorCommentCreate(CollaboratorCommentBase):
    pass

class CollaboratorCommentResponse(CollaboratorCommentBase):
    id: str
    project_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

