"""Per-scene wardrobe lookup and the add-missing-columns migration."""
import json

from sqlalchemy import create_engine, inspect, text

from app.database import _add_missing_columns
from app.shot_prompt_builder import resolve_wardrobe

WARDROBE = json.dumps({"default": "olive uniform", "by_scene": {"3": "cream shirt and grey trousers"}})


def test_scene_override_wins_over_default():
    assert resolve_wardrobe(WARDROBE, 3) == "cream shirt and grey trousers"


def test_default_used_for_other_scenes_and_portraits():
    assert resolve_wardrobe(WARDROBE, 1) == "olive uniform"
    assert resolve_wardrobe(WARDROBE, None) == "olive uniform"


def test_missing_or_bad_wardrobe_is_empty():
    assert resolve_wardrobe(None, 1) == ""
    assert resolve_wardrobe("not json", 1) == ""
    assert resolve_wardrobe(json.dumps(["x"]), 1) == ""


def test_migration_adds_columns_to_existing_tables_and_is_idempotent():
    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY, title VARCHAR)"))
        conn.execute(text("CREATE TABLE characters (id VARCHAR PRIMARY KEY, name VARCHAR)"))
        _add_missing_columns(conn)
        _add_missing_columns(conn)   # second run must not fail
        cols = {t: {c["name"] for c in inspect(conn).get_columns(t)} for t in ("projects", "characters")}
    assert "period" in cols["projects"]
    assert "wardrobe" in cols["characters"]
