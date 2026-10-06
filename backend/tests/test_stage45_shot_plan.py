"""
Stage 4 + 5 tests — LLM refinement + cinematography plan on top of the rules
engine. The LLM call is mocked throughout; validation/repair/fallback logic
is what's under test here (the rules engine itself is tested separately in
test_shot_planner.py).
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai_service import generate_shot_plan, _validate_stage45_structure, _fallback_stage45_plan
from app.shot_planner import SHOT_TYPES

SCENE = {
    "heading": "INT. VASANTH ROOM - EVENING",
    "characters_present": ["VASANTH", "RUKHMIKA"],
    "raw_action": "Vasanth dials a number, phone shaking in his hand.",
    "key_objects": ["phone"],
    "emotion": "nervous",
    "conflict": "",
    "visual_emphasis": "His hands and the phone screen.",
}


def valid_shot(shot_type="Close-Up"):
    return {
        "shot_type": shot_type,
        "reasoning": "Captures his nervous anticipation.",
        "shot_size": "Close-Up",
        "camera_angle": "Eye Level",
        "lens_mm": 85,
        "camera_height": "Chest height",
        "movement": "Static",
        "framing": "Tight on the face.",
        "composition_notes": "Rule of thirds, eyes in upper third.",
        "lighting": {"key": "Soft key", "fill": "Ambient", "backlight": "", "practicals": "Lamp",
                     "quality": "Soft", "direction": "Front", "intensity": "Low", "color_temp_k": 3200},
        "mood": "Nervous",
        "color_palette": "Warm amber",
        "contrast": "Medium",
        "depth_of_field": "Shallow",
        "perspective_notes": "",
    }


def valid_response(shot_types=("Close-Up", "Insert")):
    return json.dumps({"shots": [valid_shot(st) for st in shot_types]})


# ── _validate_stage45_structure ──────────────────────────────────────────────

def test_validate_accepts_well_formed_plan():
    assert _validate_stage45_structure(json.loads(valid_response())) == []

def test_validate_rejects_invalid_shot_type():
    data = json.loads(valid_response())
    data["shots"][0]["shot_type"] = "Extreme Wide Panoramic Drone Shot"
    errors = _validate_stage45_structure(data)
    assert any("shot_type" in e for e in errors)

def test_validate_rejects_missing_reasoning():
    data = json.loads(valid_response())
    data["shots"][0]["reasoning"] = ""
    errors = _validate_stage45_structure(data)
    assert any("reasoning" in e for e in errors)

def test_validate_rejects_non_integer_lens_mm():
    data = json.loads(valid_response())
    data["shots"][0]["lens_mm"] = "wide"
    errors = _validate_stage45_structure(data)
    assert any("lens_mm" in e for e in errors)

def test_validate_rejects_missing_lighting_key():
    data = json.loads(valid_response())
    data["shots"][0]["lighting"] = {"quality": "Soft"}
    errors = _validate_stage45_structure(data)
    assert any("lighting" in e for e in errors)


# ── _fallback_stage45_plan ───────────────────────────────────────────────────

def test_fallback_produces_valid_plan_from_rules_alone():
    rule_suggestions = [{"shot_type": "Close-Up", "rule_reasoning": "Test reasoning."}]
    result = _fallback_stage45_plan(rule_suggestions)
    assert _validate_stage45_structure(result) == []
    assert result["shots"][0]["reasoning"] == "Test reasoning."


# ── generate_shot_plan (end-to-end with mocked LLM) ─────────────────────────

@pytest.mark.asyncio
async def test_generate_shot_plan_happy_path():
    with patch("app.ai_service.call_llm", new=AsyncMock(return_value=valid_response())):
        shots = await generate_shot_plan(SCENE, is_first_scene_at_location=False)
    assert len(shots) == 2
    assert all(s["shot_type"] in SHOT_TYPES for s in shots)
    assert all(s["reasoning"] for s in shots)

@pytest.mark.asyncio
async def test_generate_shot_plan_repairs_invalid_response():
    mock = AsyncMock(side_effect=["not json", valid_response()])
    with patch("app.ai_service.call_llm", new=mock):
        shots = await generate_shot_plan(SCENE, is_first_scene_at_location=False)
    assert mock.call_count == 2
    assert len(shots) == 2

@pytest.mark.asyncio
async def test_generate_shot_plan_falls_back_to_rules_after_exhausting_retries():
    mock = AsyncMock(return_value="")  # empty response from all providers every time
    with patch("app.ai_service.call_llm", new=mock):
        shots = await generate_shot_plan(SCENE, is_first_scene_at_location=True)
    assert mock.call_count == 3  # 1 initial + 2 retries
    assert len(shots) > 0
    assert all(s["reasoning"] for s in shots)
    # Stage 4's rules engine should have suggested a phone-call pattern for this scene.
    assert any(s["shot_type"] == "Insert" for s in shots)
