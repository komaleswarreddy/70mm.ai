"""
Stage 9 tests — visual continuity QA. The color-histogram math (real
OpenCV, no mocking needed — fast, deterministic, no network/GPU) is
exercised directly; check_shot_continuity's CLIP calls are mocked so these
stay fast and don't depend on the real model load.
"""
import os
import pytest
from unittest.mock import patch
from PIL import Image, ImageDraw

from app.continuity_service import (
    check_shot_continuity, compute_color_histogram, histogram_distance,
    IDENTITY_SIMILARITY_THRESHOLD, COLOR_HISTOGRAM_DISTANCE_THRESHOLD,
)


def _make_image(path, color):
    """A flat solid color is a degenerate single-bin histogram — any two
    DIFFERENT flat colors always score exactly the same maximal chi-square
    distance regardless of how visually different they are, which isn't
    representative of real (photographic/generated) images. Use a gradient
    instead so tests exercise a realistic, continuous distance range."""
    img = Image.new("RGB", (128, 128))
    draw = ImageDraw.Draw(img)
    c1, c2 = color, tuple(max(0, c - 40) for c in color)
    for y in range(128):
        t = y / 128
        row_color = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        draw.line([(0, y), (128, y)], fill=row_color)
    img.save(path)


# ── color histogram (real OpenCV, no mocking) ───────────────────────────────

def test_histogram_distance_identical_images_is_near_zero(tmp_path):
    p1, p2 = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    _make_image(p1, (120, 50, 200))
    _make_image(p2, (120, 50, 200))
    h1, h2 = compute_color_histogram(p1), compute_color_histogram(p2)
    assert histogram_distance(h1, h2) < 0.01

def test_histogram_distance_different_colors_is_larger(tmp_path):
    p1, p2 = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    _make_image(p1, (250, 10, 10))   # red
    _make_image(p2, (10, 250, 10))   # green
    h1, h2 = compute_color_histogram(p1), compute_color_histogram(p2)
    # Bhattacharyya distance is BOUNDED 0-1 (that boundedness is exactly why
    # continuity_service switched to it from chi-square), so the old ">1.0"
    # assertion here was unsatisfiable -- two maximally different flat colours
    # measure 1.0, not more.
    assert histogram_distance(h1, h2) > 0.9

def test_compute_color_histogram_missing_file_returns_none():
    assert compute_color_histogram("/nonexistent/path.png") is None


# ── check_shot_continuity ────────────────────────────────────────────────────

def test_no_image_yet_is_not_flagged():
    result = check_shot_continuity(None, [], [])
    assert result["needs_review"] is False
    assert "No image" in result["flags"][0]

def test_flags_low_identity_similarity(tmp_path):
    shot_path = str(tmp_path / "shot.png")
    _make_image(shot_path, (100, 100, 100))
    shot_url = f"/{os.path.relpath(shot_path, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))}".replace("\\", "/")

    with patch("app.continuity_service._resolve_disk_path", side_effect=lambda u: shot_path if u == "shot" else None), \
         patch("app.continuity_service.compute_image_embedding", return_value=[1.0, 0.0]), \
         patch("app.continuity_service.cosine_similarity", return_value=0.2):  # below threshold
        result = check_shot_continuity("shot", [{"name": "Vasanth", "embedding_vector": [0.0, 1.0]}], [])

    assert result["needs_review"] is True
    assert any("Vasanth" in f for f in result["flags"])
    assert result["identity_score"] == pytest.approx(0.2)

def test_does_not_flag_when_similarity_above_threshold(tmp_path):
    shot_path = str(tmp_path / "shot.png")
    _make_image(shot_path, (100, 100, 100))

    with patch("app.continuity_service._resolve_disk_path", side_effect=lambda u: shot_path if u == "shot" else None), \
         patch("app.continuity_service.compute_image_embedding", return_value=[1.0, 0.0]), \
         patch("app.continuity_service.cosine_similarity", return_value=IDENTITY_SIMILARITY_THRESHOLD + 0.1):
        result = check_shot_continuity("shot", [{"name": "Vasanth", "embedding_vector": [0.9, 0.1]}], [])

    assert result["needs_review"] is False

def test_skips_characters_without_an_embedding(tmp_path):
    shot_path = str(tmp_path / "shot.png")
    _make_image(shot_path, (100, 100, 100))

    with patch("app.continuity_service._resolve_disk_path", side_effect=lambda u: shot_path if u == "shot" else None), \
         patch("app.continuity_service.compute_image_embedding", return_value=[1.0, 0.0]):
        result = check_shot_continuity("shot", [{"name": "Vasanth", "embedding_vector": None}], [])

    assert result["needs_review"] is False
    assert result["identity_score"] is None

def test_flags_color_grade_drift_within_scene(tmp_path):
    shot_path = str(tmp_path / "shot.png")
    other_path = str(tmp_path / "other.png")
    _make_image(shot_path, (250, 10, 10))
    _make_image(other_path, (10, 250, 10))

    def resolve(u):
        return {"shot": shot_path, "other": other_path}.get(u)

    with patch("app.continuity_service._resolve_disk_path", side_effect=resolve), \
         patch("app.continuity_service.compute_image_embedding", return_value=None):  # isolate the color check
        result = check_shot_continuity("shot", [], ["other"])

    assert result["needs_review"] is True
    assert result["color_distance"] is not None
    assert result["color_distance"] > COLOR_HISTOGRAM_DISTANCE_THRESHOLD
