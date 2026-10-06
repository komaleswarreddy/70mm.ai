"""Stage 8 production board engine: layout packing, reframes, quality of the
PNG and PDF outputs, complex-script text, and graceful fallbacks."""
import os

import numpy as np
import pytest
from PIL import Image

from app.board_service import (
    COLS, DESIGN_W, PNG_SCALE, _fit, auto_legend, compose_project_boards, cover_crop,
    is_complex_script, pack_rows, shot_tag,
)


def _scene(n, k, image=None, **shot_extra):
    return {"scene_number": n, "heading": f"INT. PLACE {n} - DAY",
            "shots": [{"shot_number": i + 1, "shot_size": "Medium Shot", "lens": "35mm", "movement": "Static",
                       "caption": f"Shot {n}.{i + 1} action.", "dialogue": "", "crop": None, "image_path": image,
                       **shot_extra} for i in range(k)]}


def _labels(rows):
    out = []
    for r in rows:
        row = []
        for it in r:
            row.append(f"{it[1]['scene_number']}.{it[2]['shot_number']}" if it[0] == "shot"
                       else it[0] + (str(it[1]) if it[0] == "end" else ""))
        out.append(row)
    return out


def test_pack_rows_reproduces_the_approved_letters_to_sita_layout():
    rows = pack_rows([_scene(1, 2), _scene(2, 6), _scene(3, 7), _scene(4, 5)])
    assert _labels(rows) == [
        ["1.1", "1.2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6"],
        ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "cast"],
        ["4.1", "4.2", "4.3", "4.4", "4.5", "end3"],
    ]


def test_a_full_row_never_receives_the_cast_card():
    """Regression: a full row was recorded as a zero-width 'gap' and the cast
    card was pushed into a ninth column off the sheet."""
    rows = pack_rows([_scene(1, 8), _scene(2, 3)])
    assert all(len(r) <= COLS for r in rows)
    assert _labels(rows)[1][:4] == ["2.1", "2.2", "2.3", "cast"]


def test_long_scene_splits_across_rows_and_marks_continuation():
    rows = pack_rows([_scene(1, 11)])
    assert len(rows[0]) == COLS
    first_of_row2 = rows[1][0]
    assert first_of_row2[0] == "shot" and first_of_row2[3] is True   # continued
    assert rows[-1][-1][0] == "end"


def test_empty_project_still_gets_cast_and_end_cards():
    assert _labels(pack_rows([])) == [["cast", f"end{COLS - 1}"]]


def test_cover_crop_applies_the_reframe_then_fits_the_panel_aspect():
    l, t, r, b = cover_crop((1024, 640), (290, 290, 850, 640), 16 / 10)
    assert 290 <= l < r <= 850 and 290 <= t < b <= 640
    assert abs((r - l) / (b - t) - 1.6) < 0.01
    assert cover_crop((1024, 640), None, 1.6) == (0, 0, 1024, 640)


def test_shot_tags_and_complex_script_detection():
    assert shot_tag("Over-the-Shoulder") == "OVER THE SHOULDER"
    assert shot_tag("Medium") == "MEDIUM SHOT"
    assert is_complex_script("ఇట్లు, సీతామహాలక్ష్మి")
    assert not is_complex_script("Curious → reflective “Do I know you?”")


def test_fit_never_ends_on_a_dangling_word():
    assert _fit("Pan following the convoy", "sans", 21, 160) == "Pan following"


def test_auto_legend_derives_lens_ranges_and_reframes():
    scenes = [_scene(1, 1, lens="24mm"), _scene(2, 1, lens="85mm")]
    legend = auto_legend(scenes, "India, 1965", ["2.1"])
    assert legend["lens_guide"][0] == "Wide 24mm" and legend["lens_guide"][2] == "Tele 85mm"
    assert "2.1" in legend["notes"][0]


def _frame(tmp_path, name="shot.png"):
    arr = (np.random.default_rng(0).random((640, 1024, 3)) * 255).astype("uint8")
    path = tmp_path / name
    Image.fromarray(arr).save(path)
    return str(path)


def test_compose_writes_7200px_png_and_pdf_with_full_resolution_shots(tmp_path):
    frame = _frame(tmp_path)
    project = {"title": "Test Film", "period": "India, 1965", "characters": [],
               "scenes": [_scene(1, 2, image=frame), _scene(2, 1, image=frame, crop=[290, 290, 850, 640])]}
    out, cached = compose_project_boards(project, {"tagline": "A tagline", "end_lines": ["The end."]}, "t", out_dir=str(tmp_path))
    assert cached is False
    assert len(out) == 1
    with Image.open(out[0]["png_path"]) as im:
        assert im.width == int(DESIGN_W * PNG_SCALE)

    from pypdf import PdfReader
    reader = PdfReader(out[0]["pdf_path"])
    assert len(reader.pages) == 1
    sizes = sorted((img.image.width, img.image.height) for img in reader.pages[0].images)
    # uncropped shots are embedded at their full 1024x640 source resolution
    # (ReportLab stores the two identical frames once); the reframed shot keeps
    # every source pixel of its crop (560x350) -- nothing is downsampled.
    assert (1024, 640) in sizes
    assert (560, 350) in sizes
    assert all(w >= 560 for w, _ in sizes)


def test_compose_handles_missing_images_and_telugu_text(tmp_path):
    project = {"title": "Test", "period": "", "characters": [], "scenes": [_scene(1, 3, image=None)]}
    settings = {"title_native": "ఇట్లు, సీతామహాలక్ష్మి", "tagline": "కురుక్షేత్రంలో రావణ సంహారం…",
                "end_lines": ["నాలుగు మాటలు పోగేసి ఉత్తరం రాస్తే,"], "signature": "ఇట్లు, సీత"}
    out, _ = compose_project_boards(project, settings, "t2", out_dir=str(tmp_path))
    assert os.path.getsize(out[0]["png_path"]) > 0 and open(out[0]["pdf_path"], "rb").read(4) == b"%PDF"


def test_many_shots_split_into_numbered_boards(tmp_path):
    frame = _frame(tmp_path)
    scenes = [_scene(n, 8, image=frame) for n in range(1, 5)]      # 32 shots -> 2 sheets
    out, _ = compose_project_boards({"title": "Long", "period": "", "characters": [], "scenes": scenes}, {}, "t3",
                                    out_dir=str(tmp_path))
    assert [b["board_number"] for b in out] == [1, 2]
    assert all(b["total"] == 2 for b in out)
    assert out[0]["scene_range"] == [1, 3] and out[1]["scene_range"] == [4, 4]


def test_unchanged_recompose_is_served_from_cache_and_changes_invalidate_it(tmp_path):
    import time
    frame = _frame(tmp_path)
    project = {"title": "Cache", "period": "", "characters": [], "scenes": [_scene(1, 2, image=frame)]}
    first, cached = compose_project_boards(project, {}, "c", out_dir=str(tmp_path))
    assert cached is False and os.path.exists(first[0]["preview_path"])
    png_mtime = os.stat(first[0]["png_path"]).st_mtime_ns

    t = time.time()
    again, cached = compose_project_boards(project, {}, "c", out_dir=str(tmp_path))
    assert cached is True and time.time() - t < 1.0
    assert os.stat(again[0]["png_path"]).st_mtime_ns == png_mtime        # not re-rendered

    project["scenes"][0]["shots"][0]["caption"] = "An edited caption."   # text change
    _, cached = compose_project_boards(project, {}, "c", out_dir=str(tmp_path))
    assert cached is False

    os.utime(frame, ns=(time.time_ns(), time.time_ns() + 10**9))           # image regenerated
    _, cached = compose_project_boards(project, {}, "c", out_dir=str(tmp_path))
    assert cached is False

    _, cached = compose_project_boards(project, {}, "c", out_dir=str(tmp_path), force=True)
    assert cached is False
