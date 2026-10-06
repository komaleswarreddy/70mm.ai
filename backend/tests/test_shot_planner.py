"""
Stage 4 rules engine tests — deterministic, no LLM involved at all.
"""
from app.shot_planner import (
    suggest_shot_plan, default_cinematography_for_shot_type, infer_characters_in_shot, SHOT_TYPES,
)


def test_establishing_arrival_gets_wide_establishing_first():
    scene = {"raw_action": "Vasanth's motorbike rolls up outside the gate.", "key_objects": ["motorbike"],
              "characters_present": ["VASANTH"], "emotion": "", "conflict": ""}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=True)
    assert plan[0]["shot_type"] == "Wide Establishing"

def test_phone_call_gets_close_ups_and_insert():
    scene = {"raw_action": "Vasanth dials a number, phone shaking.", "key_objects": ["phone"],
              "characters_present": ["VASANTH", "RUKHMIKA"], "emotion": "", "conflict": ""}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=False)
    shot_types = [s["shot_type"] for s in plan]
    assert shot_types.count("Close-Up") >= 2
    assert "Insert" in shot_types
    assert "Two-Shot" in shot_types

def test_group_scene_gets_wide_medium_and_reaction_closeups():
    scene = {"raw_action": "Ramesh, Raju, Vasanth arrive together.", "key_objects": [],
              "characters_present": ["RAMESH", "RAJU", "VASANTH"], "emotion": "", "conflict": ""}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=False)
    shot_types = [s["shot_type"] for s in plan]
    assert "Wide" in shot_types
    assert "Medium" in shot_types
    assert shot_types.count("Close-Up") >= 3

def test_conflict_scene_gets_ots_and_two_shot():
    scene = {"raw_action": "They argue.", "key_objects": [], "characters_present": ["PRIYA", "RAJU"],
              "emotion": "furious", "conflict": "Priya confronts Raju about his lies."}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=False)
    shot_types = [s["shot_type"] for s in plan]
    assert "Over-the-Shoulder" in shot_types
    assert "Two-Shot" in shot_types

def test_vehicle_action_gets_wide_medium_insert():
    scene = {"raw_action": "The bus finally pulls up, brakes hissing.", "key_objects": ["bus"],
              "characters_present": ["VASANTH"], "emotion": "", "conflict": ""}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=False)
    shot_types = [s["shot_type"] for s in plan]
    assert "Wide" in shot_types
    assert "Insert" in shot_types

def test_quiet_single_character_scene_fallback():
    scene = {"raw_action": "She sits alone, reading.", "key_objects": [], "characters_present": ["ANITA"],
              "emotion": "", "conflict": ""}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=False)
    assert len(plan) >= 1
    assert plan[0]["shot_type"] == "Medium"

def test_every_suggestion_has_non_empty_reasoning():
    scene = {"raw_action": "Ramesh, Raju, Vasanth argue about the plan.", "key_objects": ["phone"],
              "characters_present": ["RAMESH", "RAJU"], "emotion": "tense", "conflict": "A disagreement."}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=True)
    assert all(s["rule_reasoning"].strip() for s in plan)

def test_max_shots_cap_respected():
    scene = {"raw_action": "arrives bike phone call argue tense", "key_objects": ["phone", "motorbike"],
              "characters_present": ["A", "B", "C", "D"], "emotion": "furious", "conflict": "Everything."}
    plan = suggest_shot_plan(scene, is_first_scene_at_location=True, max_shots=4)
    assert len(plan) <= 4

def test_default_cinematography_covers_every_shot_type():
    for shot_type in SHOT_TYPES:
        defaults = default_cinematography_for_shot_type(shot_type)
        assert isinstance(defaults["lens_mm"], int)
        assert defaults["camera_angle"]
        assert defaults["depth_of_field"]

def test_default_cinematography_unknown_type_falls_back_to_medium():
    assert default_cinematography_for_shot_type("Not A Real Type") == default_cinematography_for_shot_type("Medium")


# ── infer_characters_in_shot ─────────────────────────────────────────────────

def test_infer_characters_matches_name_mentioned_in_reasoning():
    result = infer_characters_in_shot("Close-Up", "Close-up on VASANTH during the call.", ["VASANTH", "RUKHMIKA"])
    assert result == ["VASANTH"]

def test_infer_characters_matches_multiple_names_mentioned():
    result = infer_characters_in_shot("Two-Shot", "Shows both VASANTH and RUKHMIKA together.", ["VASANTH", "RUKHMIKA"])
    assert set(result) == {"VASANTH", "RUKHMIKA"}

def test_infer_characters_group_shot_type_falls_back_to_full_cast():
    result = infer_characters_in_shot("Wide", "Establishes the group.", ["RAMESH", "RAJU", "VASANTH"])
    assert result == ["RAMESH", "RAJU", "VASANTH"]

def test_infer_characters_non_group_no_match_falls_back_to_first():
    result = infer_characters_in_shot("Close-Up", "A tight shot of trembling hands.", ["PRIYA", "RAJU"])
    assert result == ["PRIYA"]

def test_infer_characters_empty_scene_cast_returns_empty():
    assert infer_characters_in_shot("Wide", "anything", []) == []
