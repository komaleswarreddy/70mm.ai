"""
Stage 3 tests — scene understanding (emotion, conflict, objects, visual
emphasis, continuity). The LLM call (`call_llm`) is mocked throughout
so these stay deterministic; the validation/repair-loop/fallback/context-
carrying logic is what's under test.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai_service import (
    understand_scenes,
    _validate_stage3_structure,
    _fallback_stage3_batch,
)

SCENES = [
    {"scene_number": 1, "heading": "INT. NURSERY - DAY", "location": "NURSERY", "time_of_day": "DAY",
     "raw_action": "Rukhmika waters plants nervously.", "raw_dialogue": [], "characters_present": ["RUKHMIKA"]},
    {"scene_number": 2, "heading": "INT. ROOM - EVENING", "location": "ROOM", "time_of_day": "EVENING",
     "raw_action": "Vasanth calls, phone shaking in his hand.", "raw_dialogue": [], "characters_present": ["VASANTH"]},
]


def valid_response(scene_numbers=(1, 2)):
    return json.dumps({
        "scenes": [
            {
                "scene_number": sn,
                "action_summary": f"Summary for scene {sn}.",
                "emotion": "tense",
                "conflict": "",
                "key_objects": ["phone"] if sn == 2 else ["plants"],
                "visual_emphasis": "Hands and face.",
                "continuity_notes": [],
            }
            for sn in scene_numbers
        ]
    })


# ── _validate_stage3_structure ──────────────────────────────────────────────

def test_validate_accepts_well_formed_structure():
    data = json.loads(valid_response())
    assert _validate_stage3_structure(data, {1, 2}) == []

def test_validate_rejects_hallucinated_scene_number():
    data = json.loads(valid_response(scene_numbers=(1, 2, 99)))
    errors = _validate_stage3_structure(data, {1, 2})
    assert any("99" in e for e in errors)

def test_validate_rejects_missing_scene():
    data = json.loads(valid_response(scene_numbers=(1,)))  # scene 2 never analyzed
    errors = _validate_stage3_structure(data, {1, 2})
    assert any("never analyzed" in e for e in errors)

def test_validate_rejects_duplicate_scene_number():
    data = json.loads(valid_response(scene_numbers=(1, 1)))
    errors = _validate_stage3_structure(data, {1})
    assert any("more than once" in e for e in errors)

def test_validate_requires_non_empty_action_summary():
    data = json.loads(valid_response())
    data["scenes"][0]["action_summary"] = ""
    errors = _validate_stage3_structure(data, {1, 2})
    assert any("action_summary" in e for e in errors)


# ── _fallback_stage3_batch ───────────────────────────────────────────────────

def test_fallback_covers_every_scene_with_no_llm_call():
    result = _fallback_stage3_batch(SCENES)
    numbers = {sc["scene_number"] for sc in result["scenes"]}
    assert numbers == {1, 2}
    assert all(sc["emotion"] == "neutral" for sc in result["scenes"])


# ── understand_scenes (end-to-end with mocked LLM) ──────────────────────────

@pytest.mark.asyncio
async def test_understand_scenes_happy_path():
    with patch("app.ai_service.call_llm", new=AsyncMock(return_value=valid_response())):
        result = await understand_scenes(SCENES, batch_size=8)
    assert set(result.keys()) == {1, 2}
    assert result[1]["emotion"] == "tense"
    assert result[2]["key_objects"] == ["phone"]

@pytest.mark.asyncio
async def test_understand_scenes_repairs_invalid_json_then_succeeds():
    mock = AsyncMock(side_effect=["garbage, not json", valid_response()])
    with patch("app.ai_service.call_llm", new=mock):
        result = await understand_scenes(SCENES, batch_size=8)
    assert mock.call_count == 2
    assert set(result.keys()) == {1, 2}

@pytest.mark.asyncio
async def test_understand_scenes_falls_back_after_exhausting_retries():
    mock = AsyncMock(return_value="still not json")
    with patch("app.ai_service.call_llm", new=mock):
        result = await understand_scenes(SCENES, batch_size=8)
    assert mock.call_count == 3  # 1 initial + 2 retries
    assert set(result.keys()) == {1, 2}
    assert result[1]["emotion"] == "neutral"

@pytest.mark.asyncio
async def test_understand_scenes_carries_prior_context_across_batches():
    # batch_size=1 forces two separate calls; the second call's prompt must
    # reference scene 1's key object ("plants") as continuity context.
    captured_prompts = []

    async def fake_call(prompt, response_schema=None):
        captured_prompts.append(prompt)
        sn = 1 if len(captured_prompts) == 1 else 2
        return valid_response(scene_numbers=(sn,))

    with patch("app.ai_service.call_llm", new=fake_call):
        result = await understand_scenes(SCENES, batch_size=1)

    assert set(result.keys()) == {1, 2}
    assert "plants" in captured_prompts[1]  # scene 1's key object carried into scene 2's prompt

@pytest.mark.asyncio
async def test_understand_scenes_empty_input():
    result = await understand_scenes([])
    assert result == {}
