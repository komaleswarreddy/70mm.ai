"""
FDX (Final Draft XML) import tests. Pure stdlib XML parsing — no external
tool or Final Draft license needed. sample_clean.fdx was hand-authored
against Final Draft's documented schema to carry the exact same screenplay
content as sample_clean_fountain.txt, so these tests prove the two formats
produce equivalent Stage 1 structured output, not just "doesn't crash."
"""
import os
import pytest

from app.universal_importer import extract_text, extract_text_from_fdx
from app.parser import parse_screenplay, structure_scenes

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture_bytes(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


def test_extract_text_from_fdx_produces_parseable_pseudo_fountain():
    text = extract_text_from_fdx(load_fixture_bytes("sample_clean.fdx"))
    assert "INT. PLANT NURSERY - DAY" in text
    assert "VASANTH" in text
    assert "(calling out)" in text

def test_extract_text_routes_fdx_extension_correctly():
    text = extract_text("screenplay.fdx", load_fixture_bytes("sample_clean.fdx"))
    assert "INT. PLANT NURSERY - DAY" in text

def test_fdx_title_page_is_not_treated_as_screenplay_content():
    text = extract_text_from_fdx(load_fixture_bytes("sample_clean.fdx"))
    assert "THE LAST BUS HOME" not in text  # lives in <TitlePage>, never traversed

def test_invalid_xml_raises_clear_error():
    with pytest.raises(ValueError, match="not valid XML"):
        extract_text_from_fdx(b"this is not xml at all")

def test_empty_fdx_raises_clear_error():
    empty = b'<?xml version="1.0"?><FinalDraft><Content></Content></FinalDraft>'
    with pytest.raises(ValueError, match="no recognizable screenplay content"):
        extract_text_from_fdx(empty)


# ── Equivalence with the plain-text/Fountain version of the same content ───

def _fountain_scenes():
    text = load_fixture_bytes("sample_clean_fountain.txt").decode("utf-8")
    parsed = parse_screenplay(text)
    return structure_scenes(parsed), parsed["characters"]

def _fdx_scenes():
    text = extract_text_from_fdx(load_fixture_bytes("sample_clean.fdx"))
    parsed = parse_screenplay(text)
    return structure_scenes(parsed), parsed["characters"]

def test_fdx_produces_the_same_scene_count_as_the_fountain_equivalent():
    fountain_scenes, _ = _fountain_scenes()
    fdx_scenes, _ = _fdx_scenes()
    assert len(fdx_scenes) == len(fountain_scenes) == 3

def test_fdx_produces_the_same_characters_as_the_fountain_equivalent():
    _, fountain_chars = _fountain_scenes()
    _, fdx_chars = _fdx_scenes()
    assert fdx_chars == fountain_chars == ["RUKHMIKA", "VASANTH"]

def test_fdx_produces_the_same_slugline_breakdown_as_the_fountain_equivalent():
    fountain_scenes, _ = _fountain_scenes()
    fdx_scenes, _ = _fdx_scenes()
    for f_scene, x_scene in zip(fountain_scenes, fdx_scenes):
        assert x_scene["int_ext"] == f_scene["int_ext"]
        assert x_scene["location"] == f_scene["location"]
        assert x_scene["time_of_day"] == f_scene["time_of_day"]
        assert x_scene["characters_present"] == f_scene["characters_present"]

def test_fdx_produces_the_same_dialogue_as_the_fountain_equivalent():
    fountain_scenes, _ = _fountain_scenes()
    fdx_scenes, _ = _fdx_scenes()
    for f_scene, x_scene in zip(fountain_scenes, fdx_scenes):
        assert len(x_scene["raw_dialogue"]) == len(f_scene["raw_dialogue"])
        for f_line, x_line in zip(f_scene["raw_dialogue"], x_scene["raw_dialogue"]):
            assert x_line["character"] == f_line["character"]
