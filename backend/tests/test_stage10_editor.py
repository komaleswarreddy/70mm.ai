"""
Stage 10 tests — natural-language shot editor. The LLM call is mocked
throughout (same pattern as Stages 2/3/4-5/10); the fallback keyword
translator is tested against the spec's own worked examples directly.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai_service import translate_shot_edit, _validate_edit_diff, _fallback_edit_diff

CURRENT_SHOT = {
    "shot_type": "Medium", "shot_size": "Medium Shot", "angle": "Eye Level", "lens_mm": 35,
    "movement": "Static", "camera_height": None, "framing": None, "composition_notes": None,
    "contrast": "Medium", "depth_of_field": "Medium", "perspective_notes": None,
    "color_palette": "Natural", "mood": "Neutral", "day_night": "Day",
}


# ── _validate_edit_diff ──────────────────────────────────────────────────────

def test_validate_accepts_a_valid_single_field_diff():
    assert _validate_edit_diff({"angle": "Low"}) == []

def test_validate_rejects_unknown_field():
    errors = _validate_edit_diff({"not_a_real_field": "x"})
    assert any("Unknown field" in e for e in errors)

def test_validate_rejects_invalid_shot_type():
    errors = _validate_edit_diff({"shot_type": "Extreme Drone Shot"})
    assert any("shot_type" in e for e in errors)

def test_validate_rejects_non_integer_lens_mm():
    errors = _validate_edit_diff({"lens_mm": "wide"})
    assert any("lens_mm" in e for e in errors)

def test_validate_rejects_empty_diff():
    errors = _validate_edit_diff({})
    assert any("at least one changed field" in e for e in errors)


# ── _fallback_edit_diff — spec's own worked examples ────────────────────────

def test_fallback_low_angle_instruction():
    assert _fallback_edit_diff("make this a low-angle shot") == {"angle": "Low"}

def test_fallback_lens_instruction():
    assert _fallback_edit_diff("use a 50mm lens") == {"lens_mm": 50}

def test_fallback_night_instruction():
    assert _fallback_edit_diff("change to night") == {"day_night": "Night"}

def test_fallback_combines_multiple_cues():
    diff = _fallback_edit_diff("use a 85mm lens at night with a dolly move")
    assert diff == {"lens_mm": 85, "day_night": "Night", "movement": "Dolly"}

def test_fallback_no_recognizable_cue_returns_empty():
    assert _fallback_edit_diff("make it feel more like a memory") == {}


# ── translate_shot_edit (end-to-end with mocked LLM) ────────────────────────

@pytest.mark.asyncio
async def test_translate_shot_edit_happy_path():
    with patch("app.ai_service.call_llm", new=AsyncMock(return_value=json.dumps({"angle": "Low"}))):
        diff = await translate_shot_edit(CURRENT_SHOT, "make this a low-angle shot")
    assert diff == {"angle": "Low"}

@pytest.mark.asyncio
async def test_translate_shot_edit_repairs_invalid_response():
    mock = AsyncMock(side_effect=["not json", json.dumps({"lens_mm": 50})])
    with patch("app.ai_service.call_llm", new=mock):
        diff = await translate_shot_edit(CURRENT_SHOT, "use a 50mm lens")
    assert mock.call_count == 2
    assert diff == {"lens_mm": 50}

@pytest.mark.asyncio
async def test_translate_shot_edit_falls_back_after_exhausting_retries():
    mock = AsyncMock(return_value="")  # every provider fails every time
    with patch("app.ai_service.call_llm", new=mock):
        diff = await translate_shot_edit(CURRENT_SHOT, "change to night")
    assert mock.call_count == 3  # 1 initial + 2 retries
    assert diff == {"day_night": "Night"}  # deterministic fallback still produces the right change
