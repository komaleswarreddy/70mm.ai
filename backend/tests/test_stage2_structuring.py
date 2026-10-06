"""
Stage 2 tests — Acts -> Sequences -> Beats structuring. The LLM call itself
(`call_llm`) is mocked throughout so these stay deterministic and
don't depend on network access or the real Groq API;
the parser/schema-validation/repair-loop/merge logic is what's under test.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai_service import (
    structure_screenplay,
    _validate_stage2_structure,
    _merge_stage2_acts,
    _fallback_stage2_batch,
)

SCENES = [
    {"scene_number": 1, "heading": "INT. NURSERY - DAY", "raw_action": "Rukhmika waters plants.", "characters_present": ["RUKHMIKA"]},
    {"scene_number": 2, "heading": "INT. ROOM - EVENING", "raw_action": "Vasanth calls.", "characters_present": ["VASANTH"]},
    {"scene_number": 3, "heading": "EXT. BUS STOP - MORNING", "raw_action": "He waits.", "characters_present": ["VASANTH"]},
]


def valid_response(act_number=1, scene_numbers=(1, 2, 3), summary="A summary."):
    return json.dumps({
        "acts": [{
            "act_number": act_number,
            "title": "Act One",
            "sequences": [{
                "sequence_title": "Opening",
                "scene_numbers": list(scene_numbers),
                "beats": [{"beat_title": "Setup", "scene_numbers": list(scene_numbers), "beat_purpose": "Establish the world."}],
            }],
        }],
        "running_summary": summary,
    })


# ── _validate_stage2_structure ──────────────────────────────────────────────

def test_validate_accepts_well_formed_structure():
    data = json.loads(valid_response())
    assert _validate_stage2_structure(data, {1, 2, 3}) == []

def test_validate_rejects_non_dict():
    assert _validate_stage2_structure(["not", "a", "dict"], {1}) != []

def test_validate_rejects_hallucinated_scene_number():
    data = json.loads(valid_response(scene_numbers=(1, 2, 99)))
    errors = _validate_stage2_structure(data, {1, 2, 3})
    assert any("99" in e for e in errors)

def test_validate_rejects_missing_scene_number():
    data = json.loads(valid_response(scene_numbers=(1, 2)))  # scene 3 never assigned
    errors = _validate_stage2_structure(data, {1, 2, 3})
    assert any("never assigned" in e for e in errors)

def test_validate_requires_running_summary():
    data = json.loads(valid_response())
    data["running_summary"] = ""
    errors = _validate_stage2_structure(data, {1, 2, 3})
    assert any("running_summary" in e for e in errors)


# ── _merge_stage2_acts ───────────────────────────────────────────────────────

def test_merge_extends_same_act_number():
    acts = [{"act_number": 1, "title": "Act One", "sequences": [{"sequence_title": "A", "scene_numbers": [1], "beats": []}]}]
    new_acts = [{"act_number": 1, "title": "Act One", "sequences": [{"sequence_title": "B", "scene_numbers": [2], "beats": []}]}]
    _merge_stage2_acts(acts, new_acts)
    assert len(acts) == 1
    assert len(acts[0]["sequences"]) == 2

def test_merge_appends_new_act_number():
    acts = [{"act_number": 1, "title": "Act One", "sequences": [{"sequence_title": "A", "scene_numbers": [1], "beats": []}]}]
    new_acts = [{"act_number": 2, "title": "Act Two", "sequences": [{"sequence_title": "B", "scene_numbers": [2], "beats": []}]}]
    _merge_stage2_acts(acts, new_acts)
    assert len(acts) == 2


# ── _fallback_stage2_batch ───────────────────────────────────────────────────

def test_fallback_covers_every_scene_with_no_llm_call():
    result = _fallback_stage2_batch(SCENES)
    covered = {sn for beat in result["acts"][0]["sequences"][0]["beats"] for sn in beat["scene_numbers"]}
    assert covered == {1, 2, 3}
    assert "fallback" in result["acts"][0]["title"].lower()


# ── structure_screenplay (end-to-end with mocked LLM) ────────────────────────

@pytest.mark.asyncio
async def test_structure_screenplay_happy_path_single_batch():
    with patch("app.ai_service.call_llm", new=AsyncMock(return_value=valid_response())):
        result = await structure_screenplay(SCENES, batch_size=30)
    assert len(result["acts"]) == 1
    assert result["acts"][0]["act_number"] == 1

@pytest.mark.asyncio
async def test_structure_screenplay_repairs_invalid_json_then_succeeds():
    mock = AsyncMock(side_effect=["not valid json at all", valid_response()])
    with patch("app.ai_service.call_llm", new=mock):
        result = await structure_screenplay(SCENES, batch_size=30)
    assert mock.call_count == 2  # first attempt failed, repair retry succeeded
    assert len(result["acts"]) == 1

@pytest.mark.asyncio
async def test_structure_screenplay_falls_back_after_exhausting_retries():
    # Every attempt returns garbage -> after max_retries (2) it must fall back
    # deterministically rather than raise or drop scenes.
    mock = AsyncMock(return_value="still not json")
    with patch("app.ai_service.call_llm", new=mock):
        result = await structure_screenplay(SCENES, batch_size=30)
    assert mock.call_count == 3  # 1 initial + 2 retries
    covered = {sn for act in result["acts"] for seq in act["sequences"] for beat in seq["beats"] for sn in beat["scene_numbers"]}
    assert covered == {1, 2, 3}

@pytest.mark.asyncio
async def test_structure_screenplay_merges_across_batches():
    # batch 1 (scenes 1-2) ends act 1; batch 2 (scene 3) continues act 1 -> must merge into ONE act.
    responses = [
        valid_response(act_number=1, scene_numbers=(1, 2), summary="So far: setup."),
        valid_response(act_number=1, scene_numbers=(3,), summary="So far: setup continues."),
    ]
    mock = AsyncMock(side_effect=responses)
    with patch("app.ai_service.call_llm", new=mock):
        result = await structure_screenplay(SCENES, batch_size=2)
    assert len(result["acts"]) == 1
    assert len(result["acts"][0]["sequences"]) == 2  # one sequence per batch, merged into the same act

@pytest.mark.asyncio
async def test_structure_screenplay_empty_input():
    result = await structure_screenplay([])
    assert result == {"acts": []}
