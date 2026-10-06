"""Stage 7 quality-gate tests.

The severity split is the load-bearing behaviour here: anatomy/wardrobe/
missing-character defects must BLOCK (they made frames unusable), while
garbled insignia text must NOT -- a frame otherwise verified as good failed
purely on "garbled text on the uniform epaulette", and treating that as
blocking would fail every uniformed shot and retry forever against an
artefact that does not improve with another seed.
"""
import numpy as np
import cv2
import pytest

from app.image_qa import (
    REAL_IMAGE_SIZE,
    PLACEHOLDER_IMAGE_SIZE,
    _shot_sizes_roughly_agree,
    assess_shot,
    classify_image,
)


def _write(path, size):
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = (40, 30, 20)
    cv2.imwrite(str(path), img)


def test_classify_image_distinguishes_real_from_placeholder(tmp_path):
    real, ph = tmp_path / "real.png", tmp_path / "ph.png"
    _write(real, REAL_IMAGE_SIZE)
    _write(ph, PLACEHOLDER_IMAGE_SIZE)
    assert classify_image(str(real)) == "REAL"
    assert classify_image(str(ph)) == "PLACEHOLDER"

def test_classify_image_missing_file():
    assert classify_image("/nonexistent/x.png") == "FILE-MISSING"
    assert classify_image("") == "FILE-MISSING"

def test_placeholder_fails_the_gate_without_calling_vision(tmp_path):
    ph = tmp_path / "ph.png"
    _write(ph, PLACEHOLDER_IMAGE_SIZE)
    r = assess_shot(str(ph), "anything", expected_people=1, require_people_check=True, use_vision=False)
    assert r["passed"] is False
    assert any("PLACEHOLDER" in p for p in r["problems"])

def test_shot_size_agreement_is_case_insensitive():
    # Regression: lowercase family keys were compared against a raw "Medium",
    # so a real mismatch silently reported "can't tell".
    assert _shot_sizes_roughly_agree("Medium", "medium") is True
    assert _shot_sizes_roughly_agree("Medium", "close-up") is False
    assert _shot_sizes_roughly_agree("Wide Shot", "close-up") is False

def test_shot_size_agreement_tolerates_adjacent_and_unknown():
    assert _shot_sizes_roughly_agree("Close-Up", "medium close-up") is True
    assert _shot_sizes_roughly_agree("Two-Shot", "medium") is True
    assert _shot_sizes_roughly_agree(None, "medium") is True      # unknown -> no complaint
    assert _shot_sizes_roughly_agree("", "medium") is True

def test_gate_returns_separate_blocking_and_cosmetic_buckets(tmp_path):
    real = tmp_path / "real.png"
    _write(real, REAL_IMAGE_SIZE)
    r = assess_shot(str(real), "a frame", expected_people=1, require_people_check=False, use_vision=False)
    assert "problems" in r and "cosmetic" in r
    assert isinstance(r["problems"], list) and isinstance(r["cosmetic"], list)


def test_face_crop_box_stays_inside_the_frame():
    """A face near an edge must not produce an out-of-bounds crop."""
    from app.face_identity import crop_box
    l, t, r, b = crop_box({"x": 960, "y": 20, "w": 60, "h": 70}, 1024, 640)
    assert 0 <= l < r <= 1024 and 0 <= t < b <= 640
    assert (r - l) == (b - t)          # square
    l, t, r, b = crop_box({"x": 400, "y": 200, "w": 300, "h": 340}, 1024, 640)
    assert (r - l) == (b - t)
    assert r <= 1024 and b <= 640


def test_garbled_text_is_cosmetic_even_from_a_blocking_bucket():
    """Regression: a live run retried a good frame on 'Garbled text on
    nameplate badge' because the reviewer filed it under a blocking key.
    Severity must follow the finding's text, not which bucket it arrived in."""
    from app.image_qa import _is_cosmetic_artifact
    for s in ("Garbled text on nameplate badge", "Illegible text on shoulder insignia",
              "garbled writing on the letter", "distorted text on badge"):
        assert _is_cosmetic_artifact(s) is True, s
    for s in ("Minor finger fusion on right hand", "extra forearm holding the paper",
              "bare chest visible", "Unnatural hand placement"):
        assert _is_cosmetic_artifact(s) is False, s

def test_missing_character_is_blocking_from_any_bucket():
    from app.image_qa import _is_missing_character
    names = ["Ram", "Sita"]
    for s in ("Missing required character Ram", "Ram is absent from the frame",
              "Sita not visible in frame"):
        assert _is_missing_character(s, names) is True, s
    for s in ("garbled text on note", "warped chandelier"):
        assert _is_missing_character(s, names) is False, s


def test_wide_rendered_as_close_up_blocks_but_small_gaps_stay_cosmetic(tmp_path, monkeypatch):
    """'Wide Shot' frames came back as face close-ups and shipped because a
    shot-size mismatch was only ever cosmetic. A 3+ step gap now blocks."""
    import app.image_qa as qa
    real = tmp_path / "real.png"
    _write(real, REAL_IMAGE_SIZE)
    monkeypatch.setattr(qa, "detect_people_and_hands", lambda p: {"faces": 1, "hand_defects": []})

    def reviewer(observed):
        return lambda p, e: {"people_visible": 1, "anatomy_problems": [], "wardrobe_problems": [],
                             "other_problems": [], "shot_size_observed": observed, "verdict": "pass"}

    monkeypatch.setattr(qa, "review_with_vision", reviewer("close-up"))
    r = assess_shot(str(real), "a wide", 1, False, expected_shot_size="Wide Shot")
    assert r["passed"] is False and any("close-up" in p for p in r["problems"])

    monkeypatch.setattr(qa, "review_with_vision", reviewer("close-up"))
    r = assess_shot(str(real), "a medium", 1, False, expected_shot_size="Medium")
    assert r["passed"] is True and any("close-up" in c for c in r["cosmetic"])


def test_vision_json_parser_tolerates_think_block_and_fence():
    from app.image_qa import _extract_json
    assert _extract_json('<think>hmm</think>\n```json\n{"verdict": "pass"}\n```') == {"verdict": "pass"}
    assert _extract_json('{"people_visible": 2}') == {"people_visible": 2}


def test_vision_qa_uses_groq_not_gemini():
    import app.image_qa as qa
    assert qa.GROQ_CHAT_URL.startswith("https://api.groq.com/")
    assert "gemini" not in qa.VISION_QA_MODEL.lower()
    assert not hasattr(qa, "review_with_gemini")


def test_illegible_lettering_and_missing_props_do_not_block(tmp_path, monkeypatch):
    import app.image_qa as qa
    real = tmp_path / "real.png"
    _write(real, REAL_IMAGE_SIZE)
    monkeypatch.setattr(qa, "detect_people_and_hands", lambda p: {"faces": 1, "hand_defects": []})
    monkeypatch.setattr(qa, "review_with_vision", lambda p, e: {
        "people_visible": 2, "anatomy_problems": [], "other_problems": [], "verdict": "fail",
        "wardrobe_problems": ["Name tape on shoulder is garbled and illegible", "Dance bag is missing from Sita's feet"]})
    r = assess_shot(str(real), "x", 2, True, expected_character_names=["RAM", "SITA"])
    assert r["passed"] is True and len(r["cosmetic"]) >= 2
    monkeypatch.setattr(qa, "review_with_vision", lambda p, e: {
        "people_visible": 2, "anatomy_problems": [], "other_problems": [], "verdict": "fail",
        "wardrobe_problems": ["SITA is missing from the frame"]})
    assert assess_shot(str(real), "x", 2, True, expected_character_names=["RAM", "SITA"])["passed"] is False
