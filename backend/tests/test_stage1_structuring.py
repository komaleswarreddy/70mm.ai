"""
Stage 1 acceptance tests — deterministic parse + slugline structuring against
3 real-shaped screenplay samples of varying formatting quality, per the
Storyboard & Cinematography Engine spec's Stage 1 requirement. No LLM call
is involved anywhere in this file.
"""
import os
from app.parser import parse_screenplay, structure_scenes, parse_slugline

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


# ── parse_slugline unit tests (the deterministic breakdown itself) ─────────

def test_slugline_standard():
    assert parse_slugline("INT. PLANT NURSERY - DAY") == {
        "int_ext": "INT", "location": "PLANT NURSERY", "time_of_day": "DAY"
    }

def test_slugline_ext_no_period_no_time():
    result = parse_slugline("EXT PARKING LOT")
    assert result["int_ext"] == "EXT"
    assert result["location"] == "PARKING LOT"
    assert result["time_of_day"] is None

def test_slugline_missing_time_of_day():
    result = parse_slugline("INT. KITCHEN")
    assert result["int_ext"] == "INT"
    assert result["location"] == "KITCHEN"
    assert result["time_of_day"] is None

def test_slugline_multi_dash_moving_vehicle():
    result = parse_slugline("INT./EXT. CAR - HIGHWAY - NIGHT")
    assert result["int_ext"] == "INT/EXT"
    assert result["location"] == "CAR - HIGHWAY"
    assert result["time_of_day"] == "NIGHT"

def test_slugline_est_prefix():
    result = parse_slugline("EST. CITY SKYLINE")
    assert result["int_ext"] == "EXT"
    assert result["location"] == "CITY SKYLINE"

def test_slugline_ie_prefix():
    result = parse_slugline("I/E TRAIN COMPARTMENT - MORNING")
    assert result["int_ext"] == "INT/EXT"
    assert result["location"] == "TRAIN COMPARTMENT"
    assert result["time_of_day"] == "MORNING"

def test_slugline_non_scene_heading_returns_none():
    assert parse_slugline("PROLOGUE") == {"int_ext": None, "location": None, "time_of_day": None}
    assert parse_slugline("") == {"int_ext": None, "location": None, "time_of_day": None}


# ── Sample 1: clean, well-formatted Fountain-style script ──────────────────

def test_sample1_clean_fountain_scene_count_and_structure():
    parsed = parse_screenplay(load_fixture("sample_clean_fountain.txt"))
    scenes = structure_scenes(parsed)

    assert len(scenes) == 3
    assert "VASANTH" in parsed["characters"]
    assert "RUKHMIKA" in parsed["characters"]

    scene1 = scenes[0]
    assert scene1["int_ext"] == "INT"
    assert scene1["location"] == "PLANT NURSERY"
    assert scene1["time_of_day"] == "DAY"
    assert scene1["characters_present"] == ["RUKHMIKA", "VASANTH"]
    assert "waters a row of potted plants" in scene1["raw_action"]
    assert len(scene1["raw_dialogue"]) == 2

    scene3 = scenes[2]
    assert scene3["int_ext"] == "EXT"
    assert scene3["location"] == "BUS STOP"
    assert scene3["time_of_day"] == "EARLY MORNING"
    assert scene3["characters_present"] == ["VASANTH"]


# ── Sample 2: messy first-draft formatting ──────────────────────────────────

def test_sample2_messy_draft_survives_inconsistent_formatting():
    parsed = parse_screenplay(load_fixture("sample_messy_draft.txt"))
    scenes = structure_scenes(parsed)

    # 5 sluglines in the fixture: CAR, KITCHEN, CITY SKYLINE, PARKING LOT, HOSPITAL HALLWAY
    assert len(scenes) == 5

    car_scene = scenes[0]
    assert car_scene["int_ext"] == "INT/EXT"
    assert car_scene["location"] == "CAR - HIGHWAY"
    assert car_scene["time_of_day"] == "NIGHT"

    kitchen_scene = scenes[1]
    assert kitchen_scene["location"] == "KITCHEN"
    assert kitchen_scene["time_of_day"] is None  # no dash in this messy slugline

    skyline_scene = scenes[2]
    assert skyline_scene["int_ext"] == "EXT"  # EST. -> exterior-style
    assert skyline_scene["location"] == "CITY SKYLINE"

    parking_scene = scenes[3]
    assert parking_scene["int_ext"] == "EXT"
    assert parking_scene["location"] == "PARKING LOT"
    assert parking_scene["time_of_day"] == "DUSK"
    # dual dialogue (PRIYA ^ / RAJU ^) must not break scene/character extraction
    assert "PRIYA" in parsed["characters"]
    assert "RAJU" in parsed["characters"]

    hospital_scene = scenes[4]
    assert hospital_scene["location"] == "HOSPITAL HALLWAY"
    assert hospital_scene["time_of_day"] == "CONTINUOUS"


# ── Sample 3: transitions, forced headings, and slugline edge cases ────────

def test_sample3_transitions_and_edgecases():
    parsed = parse_screenplay(load_fixture("sample_transitions_and_edgecases.txt"))
    scenes = structure_scenes(parsed)

    headings = [s["heading"] for s in scenes]
    assert "PROLOGUE" in headings          # FADE IN: before any real heading
    assert "THE OLD WORKSHOP" in headings  # forced heading via leading '.'

    train_scene = next(s for s in scenes if "TRAIN COMPARTMENT" in s["heading"])
    assert train_scene["int_ext"] == "INT/EXT"
    assert train_scene["time_of_day"] == "MORNING"

    platform_scene = next(s for s in scenes if "STATION PLATFORM" in s["heading"])
    assert platform_scene["int_ext"] == "INT"
    assert platform_scene["time_of_day"] == "DAY"

    rooftop_scene = next(s for s in scenes if "ROOFTOP" in s["heading"])
    assert rooftop_scene["int_ext"] == "EXT"
    assert rooftop_scene["time_of_day"] == "NIGHT"

    # Title/Author metadata block must be skipped, not mistaken for a scene
    assert not any(s["heading"].startswith("TITLE") for s in scenes)
