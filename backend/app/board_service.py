"""
Stage 8 — production storyboard board sheets.

Pure compositing of already-generated Stage 7 frames (never another model
call). One layout, two outputs:

  * the layout is built ONCE as a list of drawing operations in "design
    units" (a 4800-unit-wide sheet), so the PNG and the PDF can never drift
    apart;
  * `_render_png` executes it with Pillow at PNG_SCALE (7200 px wide);
  * `_render_pdf` executes it with ReportLab: English text is real vector
    type and every shot is embedded at its FULL source resolution, so zooming
    into a panel loses nothing. Complex scripts (Telugu etc.) are placed as a
    high-resolution transparent raster because ReportLab cannot shape them.

Design (header with airmail edges and postmark, colour-coded scene bands,
numbered/tagged panels with action + dialogue + lens/movement, cast-lock card,
end card, icon footer legend) was approved on the "Letters to Sita" board.
Everything project-specific comes from `settings` (Project.board_legend_settings
JSON) or is derived from the shots, so any project composes the same way.
"""
import hashlib
import io
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
BOARDS_DIR = os.path.join(STATIC_DIR, "boards")
os.makedirs(BOARDS_DIR, exist_ok=True)
BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))

# ── geometry (design units) ─────────────────────────────────────────────────
DESIGN_W = 4800
M = 70
COLS = 8
GAP = 26
PW = (DESIGN_W - 2 * M - (COLS - 1) * GAP) // COLS
IH = int(PW * 10 / 16)
CH = 168
PH = IH + CH
STRIP_H = 64
ROW_H = STRIP_H + 14 + PH + 40
ROWS_PER_BOARD = 3
FOOTER_H = 360
HEADER_H_TAGLINE = 640
HEADER_H_PLAIN = 420

# Bump whenever the layout or rendering changes, so cached boards re-render.
ENGINE_VERSION = "production-board-2"
PNG_SCALE = 1.5                      # 7200 px wide
PNG_COMPRESS_LEVEL = 3               # lossless; optimize=True took 69 s for a 2 MB saving
PREVIEW_WIDTH = 2400                 # lightweight JPEG for the on-screen preview
PDF_PT_PER_UNIT = 1684 / DESIGN_W    # A2-width page (23.4 in)
PDF_NATIVE_PX_PER_UNIT = 2.0         # resolution of complex-script text in the PDF

PAPER = (247, 242, 230)
INK = (28, 26, 24)
MUTED = (95, 88, 80)
RED = (190, 36, 40)
BLUE = (28, 58, 128)
YELLOW = (246, 206, 70)
MAROON = (122, 28, 34)
CAPTION_BG = (255, 252, 244)
SCENE_PALETTE = [(62, 102, 142), (158, 102, 36), (30, 112, 114), (160, 88, 84), (96, 84, 140), (70, 118, 70)]

# ── fonts ───────────────────────────────────────────────────────────────────
FONT_DIRS = [os.environ.get("BOARD_FONT_DIR", ""), r"C:\Windows\Fonts",
             "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/noto", "/usr/share/fonts"]
FONT_FILES = {
    "serif_b": ["georgiab.ttf", "DejaVuSerif-Bold.ttf"],
    "serif": ["georgia.ttf", "DejaVuSerif.ttf"],
    "serif_i": ["georgiai.ttf", "DejaVuSerif-Italic.ttf"],
    "pal": ["pala.ttf", "DejaVuSerif.ttf"],
    "pal_b": ["palab.ttf", "DejaVuSerif-Bold.ttf"],
    "sans": ["arial.ttf", "DejaVuSans.ttf"],
    "sans_b": ["arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "mono_b": ["courbd.ttf", "DejaVuSansMono-Bold.ttf"],
    "hand": ["segoepr.ttf", "DejaVuSerif-Italic.ttf"],
}
NATIVE_FONT_FILES = [("Nirmala.ttc", {"bold": 1, "regular": 0}), ("NotoSansTelugu-Bold.ttf", None)]


def _find(name: str) -> Optional[str]:
    for d in FONT_DIRS:
        if d and os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


def _font_path(key: str) -> str:
    for name in FONT_FILES[key]:
        path = _find(name)
        if path:
            return path
    raise FileNotFoundError(f"No font found for '{key}' (looked for {FONT_FILES[key]} in {FONT_DIRS})")


_font_cache: Dict[Tuple, ImageFont.FreeTypeFont] = {}


def pil_font(key: str, size: float) -> ImageFont.FreeTypeFont:
    size = max(1, int(round(size)))
    k = (key, size)
    if k not in _font_cache:
        if key.startswith("native"):
            bold = key == "native_b"
            for name, idx in NATIVE_FONT_FILES:
                path = _find(name)
                if path:
                    index = (idx or {}).get("bold" if bold else "regular", 0)
                    _font_cache[k] = ImageFont.truetype(path, size, index=index, layout_engine=ImageFont.Layout.RAQM)
                    break
            else:
                _font_cache[k] = pil_font("serif_b" if bold else "serif", size)
        else:
            _font_cache[k] = ImageFont.truetype(_font_path(key), size)
    return _font_cache[k]


_measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))


# Scripts whose glyphs need shaping (conjuncts, reordering, joining). Plain
# symbols above U+0590 such as arrows or curly quotes are NOT included --
# they render fine as ordinary vector text.
_COMPLEX_RANGES = ((0x0590, 0x08FF), (0x0900, 0x0DFF), (0x0E00, 0x0FFF), (0x1000, 0x109F), (0x1780, 0x17FF))


def is_complex_script(text: str) -> bool:
    return any(lo <= ord(ch) <= hi for ch in text or "" for lo, hi in _COMPLEX_RANGES)


def text_width(text: str, key: str, size: float) -> float:
    return _measure.textlength(text, font=pil_font(key, size))


def shaped_bbox(text: str, key: str, size: float) -> Tuple[float, float, float, float]:
    return _measure.textbbox((0, 0), text, font=pil_font(key, size))


# ── drawing-op recorder ─────────────────────────────────────────────────────
class Sheet:
    """Records drawing operations in design units for both renderers."""

    def __init__(self, width: int, height: int):
        self.w, self.h, self.ops = width, height, []

    def rect(self, box, fill=None, outline=None, width=0):
        self.ops.append(("rect", tuple(box), fill, outline, width))

    def line(self, pts, fill, width=1):
        self.ops.append(("line", [tuple(p) for p in pts], fill, width))

    def poly(self, pts, fill):
        self.ops.append(("poly", [tuple(p) for p in pts], fill))

    def ellipse(self, box, fill=None, outline=None, width=0):
        self.ops.append(("ellipse", tuple(box), fill, outline, width))

    def arc(self, box, start, end, fill, width):
        self.ops.append(("arc", tuple(box), start, end, fill, width))

    def text(self, x, y, text, key, size, fill=INK):
        """Left-aligned; y is the TOP of the font's ascender (Pillow's default)."""
        if is_complex_script(text):
            l, t, _, _ = shaped_bbox(text, "native_b" if key.endswith("_b") else "native", size)
            self.shaped(x, y + t, text, "native_b" if key.endswith("_b") else "native", size, fill)
            return
        self.ops.append(("text", x, y, text, key, size, fill))

    def centered(self, text, key, size, cx, y, fill=INK):
        if is_complex_script(text):
            nk = "native_b" if key.endswith("_b") else "native"
            l, t, r, b = shaped_bbox(text, nk, size)
            self.shaped(cx - (r - l) / 2, y, text, nk, size, fill)
            return b - t
        self.text(cx - text_width(text, key, size) / 2, y, text, key, size, fill)
        return size

    def shaped(self, x_left, y_top, text, key, size, fill):
        """Complex-script text; (x_left, y_top) is the ink bbox's top-left."""
        self.ops.append(("shaped", x_left, y_top, text, key, size, fill))

    def glyph(self, cx, cy, ch, key, size, fill, cw_degrees):
        self.ops.append(("glyph", cx, cy, ch, key, size, fill, cw_degrees))

    def image(self, src_path, src_crop, dest_box):
        self.ops.append(("image", src_path, tuple(src_crop), tuple(dest_box)))


# ── renderers ───────────────────────────────────────────────────────────────
def _render_png(sheet: Sheet, scale: float = PNG_SCALE) -> Image.Image:
    W, H = int(sheet.w * scale), int(sheet.h * scale)
    img = Image.new("RGB", (W, H), PAPER)
    grain = Image.effect_noise((max(1, W // 4), max(1, H // 4)), 18).resize((W, H)).convert("L")
    img = Image.composite(img, Image.new("RGB", (W, H), (236, 228, 212)), grain.point(lambda v: 255 - v // 6))
    d = ImageDraw.Draw(img)
    S = lambda v: v * scale
    for op in sheet.ops:
        kind = op[0]
        if kind == "rect":
            _, box, fill, outline, width = op
            d.rectangle([S(c) for c in box], fill=fill, outline=outline, width=max(1, round(S(width))) if outline else 0)
        elif kind == "line":
            _, pts, fill, width = op
            d.line([(S(x), S(y)) for x, y in pts], fill=fill, width=max(1, round(S(width))))
        elif kind == "poly":
            _, pts, fill = op
            d.polygon([(S(x), S(y)) for x, y in pts], fill=fill)
        elif kind == "ellipse":
            _, box, fill, outline, width = op
            d.ellipse([S(c) for c in box], fill=fill, outline=outline, width=max(1, round(S(width))) if outline else 0)
        elif kind == "arc":
            _, box, start, end, fill, width = op
            d.arc([S(c) for c in box], start, end, fill=fill, width=max(1, round(S(width))))
        elif kind == "text":
            _, x, y, text, key, size, fill = op
            d.text((S(x), S(y)), text, font=pil_font(key, S(size)), fill=fill)
        elif kind == "shaped":
            _, x, y, text, key, size, fill = op
            f = pil_font(key, S(size))
            l, t, _, _ = d.textbbox((0, 0), text, font=f)
            d.text((S(x) - l, S(y) - t), text, font=f, fill=fill)
        elif kind == "glyph":
            _, cx, cy, ch, key, size, fill, cw = op
            g = _glyph_image(ch, key, S(size), fill, cw)
            img.paste(g, (int(S(cx) - g.width / 2), int(S(cy) - g.height / 2)), g)
        elif kind == "image":
            _, src, crop, dest = op
            box = [int(round(S(c))) for c in dest]
            with Image.open(src) as im:
                panel = im.convert("RGB").crop(crop).resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
            img.paste(panel, (box[0], box[1]))
    return img


def _glyph_image(ch, key, size, fill, cw_degrees):
    side = int(size * 2)
    g = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ImageDraw.Draw(g).text((side / 2, side / 2), ch, font=pil_font(key, size), fill=fill, anchor="mm")
    return g.rotate(-cw_degrees, resample=Image.BICUBIC)


_pdf_fonts_registered = set()


def _pdf_font(key: str) -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    name = f"Board-{key}"
    if name not in _pdf_fonts_registered:
        pdfmetrics.registerFont(TTFont(name, _font_path(key)))
        _pdf_fonts_registered.add(name)
    return name


def _render_pdf(sheet: Sheet, path: str) -> None:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as pdf_canvas

    from reportlab import rl_config
    # Binary (Flate-only) image streams. ReportLab's default ASCII85 text
    # encoding runs in pure Python when its C accelerator is absent (as here):
    # 36 s and 27 MB for one board, vs 8.5 s and 22 MB -- same lossless pixels.
    rl_config.useA85 = 0

    k = PDF_PT_PER_UNIT
    Hh = sheet.h
    c = pdf_canvas.Canvas(path, pagesize=(sheet.w * k, sheet.h * k))
    c.setTitle("Storyboard board")
    c.setFillColorRGB(*[v / 255 for v in PAPER])
    c.rect(0, 0, sheet.w * k, sheet.h * k, stroke=0, fill=1)

    def col(rgb):
        return [v / 255 for v in rgb]

    def Y(y):
        return (Hh - y) * k

    for op in sheet.ops:
        kind = op[0]
        if kind == "rect":
            _, (x0, y0, x1, y1), fill, outline, width = op
            if fill:
                c.setFillColorRGB(*col(fill))
            if outline:
                c.setStrokeColorRGB(*col(outline)); c.setLineWidth(width * k)
            c.rect(x0 * k, Y(y1), (x1 - x0) * k, (y1 - y0) * k, stroke=1 if outline else 0, fill=1 if fill else 0)
        elif kind == "line":
            _, pts, fill, width = op
            c.setStrokeColorRGB(*col(fill)); c.setLineWidth(width * k)
            p = c.beginPath(); p.moveTo(pts[0][0] * k, Y(pts[0][1]))
            for x, y in pts[1:]:
                p.lineTo(x * k, Y(y))
            c.drawPath(p, stroke=1, fill=0)
        elif kind == "poly":
            _, pts, fill = op
            c.setFillColorRGB(*col(fill))
            p = c.beginPath(); p.moveTo(pts[0][0] * k, Y(pts[0][1]))
            for x, y in pts[1:]:
                p.lineTo(x * k, Y(y))
            p.close(); c.drawPath(p, stroke=0, fill=1)
        elif kind == "ellipse":
            _, (x0, y0, x1, y1), fill, outline, width = op
            if fill:
                c.setFillColorRGB(*col(fill))
            if outline:
                c.setStrokeColorRGB(*col(outline)); c.setLineWidth(width * k)
            c.ellipse(x0 * k, Y(y1), x1 * k, Y(y0), stroke=1 if outline else 0, fill=1 if fill else 0)
        elif kind == "arc":
            _, (x0, y0, x1, y1), start, end, fill, width = op
            c.setStrokeColorRGB(*col(fill)); c.setLineWidth(width * k)
            c.arc(x0 * k, Y(y1), x1 * k, Y(y0), startAng=-end, extent=end - start)
        elif kind == "text":
            _, x, y, text, key, size, fill = op
            ascent = pil_font(key, size).getmetrics()[0]
            c.setFillColorRGB(*col(fill)); c.setFont(_pdf_font(key), size * k)
            c.drawString(x * k, Y(y + ascent), text)
        elif kind == "shaped":
            _, x, y, text, key, size, fill = op
            s = PDF_NATIVE_PX_PER_UNIT
            f = pil_font(key, size * s)
            l, t, r, b = _measure.textbbox((0, 0), text, font=f)
            im = Image.new("RGBA", (int(r - l) + 4, int(b - t) + 4), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((2 - l, 2 - t), text, font=f, fill=tuple(fill) + (255,))
            w_u, h_u = im.width / s, im.height / s
            c.drawImage(ImageReader(im), (x - 2 / s) * k, Y(y - 2 / s + h_u), w_u * k, h_u * k, mask="auto")
        elif kind == "glyph":
            _, cx, cy, ch, key, size, fill, cw = op
            f = pil_font(key, size)
            ascent, descent = f.getmetrics()
            c.saveState()
            c.translate(cx * k, Y(cy)); c.rotate(-cw)
            c.setFillColorRGB(*col(fill)); c.setFont(_pdf_font(key), size * k)
            c.drawCentredString(0, -((ascent - descent) / 2) * k, ch)
            c.restoreState()
        elif kind == "image":
            _, src, crop, (x0, y0, x1, y1) = op
            with Image.open(src) as im:
                full = im.convert("RGB").crop(crop)       # original pixels, no resampling
            c.drawImage(ImageReader(full), x0 * k, Y(y1), (x1 - x0) * k, (y1 - y0) * k)
    c.showPage()
    c.save()


# ── content helpers ─────────────────────────────────────────────────────────
def _wrap(text: str, key: str, size: float, width: float) -> List[str]:
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_width(test, key, size) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


_DANGLING = {"the", "a", "an", "of", "on", "in", "to", "with", "and", "at", "for", "from", "by"}


def _fit(text: str, key: str, size: float, width: float) -> str:
    """Longest word-prefix of `text` that fits `width`; a single over-long word is cut with an ellipsis."""
    if text_width(text, key, size) <= width:
        return text
    words = text.split()
    while len(words) > 1 and text_width(" ".join(words), key, size) > width:
        words.pop()
    while len(words) > 1 and words[-1].lower() in _DANGLING:
        words.pop()                                   # never end on "the", "on", "with", ...
    out = " ".join(words)
    if text_width(out, key, size) <= width:
        return out
    while len(out) > 1 and text_width(out + "…", key, size) > width:
        out = out[:-1]
    return out + "…"


def shot_tag(shot_size: Optional[str]) -> str:
    tag = (shot_size or "SHOT").replace("-", " ").upper().strip()
    return "MEDIUM SHOT" if tag == "MEDIUM" else tag


def scene_title(scene: Dict[str, Any]) -> str:
    heading = (scene.get("heading") or "").upper().replace(" - ", " – ")
    return f"SCENE {scene['scene_number']}  ·  {heading}" if heading else f"SCENE {scene['scene_number']}"


def cover_crop(size: Tuple[int, int], crop: Optional[Sequence[int]], aspect: float) -> Tuple[int, int, int, int]:
    """Source-pixel crop box: the optional reframe, then centre-cropped to the panel aspect."""
    W, H = size
    l, t, r, b = crop if crop else (0, 0, W, H)
    l, t, r, b = max(0, l), max(0, t), min(W, r), min(H, b)
    w, h = r - l, b - t
    if w / h > aspect:
        nw = h * aspect
        l, r = l + (w - nw) / 2, l + (w - nw) / 2 + nw
    else:
        nh = w / aspect
        t, b = t + (h - nh) / 2, t + (h - nh) / 2 + nh
    return int(round(l)), int(round(t)), int(round(r)), int(round(b))


def _year(period: str) -> str:
    m = re.search(r"(1[89]\d\d|20\d\d)", period or "")
    return m.group(1) if m else ""


def auto_legend(scenes: List[Dict[str, Any]], period: str, reframed: List[str]) -> Dict[str, List[str]]:
    shots = [s for sc in scenes for s in sc["shots"]]
    moves = [s.get("movement") for s in shots if s.get("movement") and s["movement"].lower() != "static"]
    lenses = sorted({int(m) for s in shots for m in re.findall(r"\d+", s.get("lens") or "")})
    lights = list(dict.fromkeys(s.get("lighting") for s in shots if s.get("lighting")))
    moods = list(dict.fromkeys(s.get("emotion") for s in shots if s.get("emotion")))
    palettes = list(dict.fromkeys(s.get("color_palette") for s in shots if s.get("color_palette")))
    wide = [l for l in lenses if l < 35]; normal = [l for l in lenses if 35 <= l <= 55]; tele = [l for l in lenses if l > 55]
    rng = lambda xs: (f"{xs[0]}–{xs[-1]}mm" if len(xs) > 1 else f"{xs[0]}mm") if xs else "—"
    return {
        "camera_style": ["Mostly locked-off." if len(moves) <= len(shots) / 3 else "Mobile, handheld feel.",
                         f"{len(moves)} moving shot(s)." if moves else "No camera moves.", "Eye-level coverage."],
        "colour_tone": (palettes[:3] or ["Natural."]),
        "lighting": (lights[:3] or ["Natural light."]),
        "mood": [" → ".join(moods[:4])] if moods else ["—"],
        "lens_guide": [f"Wide {rng(wide)}", f"Normal {rng(normal)}", f"Tele {rng(tele)}"],
        "notes": ([f"Reframed in post: {', '.join(reframed)}."] if reframed else []) + ([period] if period else []),
    }


# ── layout ──────────────────────────────────────────────────────────────────
def pack_rows(scenes: List[Dict[str, Any]], cols: int = COLS):
    """Rows of items: ("shot", scene, shot, continued) | ("cast",) | ("end", span).

    A scene that fits in a full row is never split; if it does not fit in what
    is left of the current row it starts a new row and the leftover slots are
    a gap. The cast-lock card fills the first gap (or goes before the end
    card); the end card spans whatever is left of the last row.
    """
    rows, cur, gaps = [], [], []
    for sc in scenes:
        shots = sc["shots"]
        if not shots:
            continue
        if cur and len(shots) > cols - len(cur) and len(shots) <= cols:
            if len(cur) < cols:                      # a full row has no gap to offer
                gaps.append((len(rows), len(cur)))
            rows.append(cur); cur = []
        for i, sh in enumerate(shots):
            if len(cur) == cols:
                rows.append(cur); cur = []
            cur.append(("shot", sc, sh, i > 0 and len(cur) == 0))
    if gaps:
        r, c = gaps[0]
        rows[r] = rows[r][:c] + [("cast",)] + rows[r][c:]
    elif len(cur) < cols:
        cur.append(("cast",))
    else:
        rows.append(cur); cur = [("cast",)]
    if cols - len(cur) < 2:
        rows.append(cur); cur = []
    cur.append(("end", cols - len(cur)))
    rows.append(cur)
    return rows


def build_sheets(project: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenes = project["scenes"]
    rows = pack_rows(scenes)
    chunks = [rows[i:i + ROWS_PER_BOARD] for i in range(0, len(rows), ROWS_PER_BOARD)]
    total = len(chunks)
    reframed = [f"{sc['scene_number']}.{sh['shot_number']}" for sc in scenes for sh in sc["shots"] if sh.get("crop")]
    legend = {**auto_legend(scenes, project.get("period") or "", reframed), **(settings.get("legend") or {})}
    color_of = {sc["scene_number"]: tuple(settings.get("scene_colors", {}).get(str(sc["scene_number"]),
                                                                             SCENE_PALETTE[i % len(SCENE_PALETTE)]))
                for i, sc in enumerate(scenes)}
    out = []
    for n, chunk in enumerate(chunks, start=1):
        board_scenes = sorted({it[1]["scene_number"] for row in chunk for it in row if it[0] == "shot"})
        header_h = HEADER_H_TAGLINE if settings.get("tagline") else HEADER_H_PLAIN
        H = header_h + len(chunk) * ROW_H + FOOTER_H + M
        sh = Sheet(DESIGN_W, H)
        n_shots = sum(1 for row in chunk for it in row if it[0] == "shot")
        _draw_header(sh, project, settings, n, total, board_scenes, n_shots, header_h)
        y = header_h + 10
        for row in chunk:
            _draw_row(sh, row, y, project, settings, color_of)
            y += ROW_H
        _draw_footer(sh, H, legend, settings, project, n, total)
        out.append({"board_number": n, "total": total, "sheet": sh,
                    "scene_range": (board_scenes[0], board_scenes[-1]) if board_scenes else (0, 0),
                    "shot_count": n_shots})
    return out


def _airmail_edge(sh: Sheet, y: float, h: float = 26):
    step = 64
    for i, x in enumerate(range(-int(h), DESIGN_W + step, step)):
        sh.poly([(x, y + h), (x + h, y), (x + h + step // 2, y), (x + step // 2, y + h)], RED if i % 2 == 0 else BLUE)


def _boxed(sh: Sheet, x, y, w, h, lines):
    sh.rect([x, y, x + w, y + h], outline=INK, width=4)
    ty = y + (h - sum(size + 10 for _, _, size in lines)) / 2
    for text, key, size in lines:
        sh.centered(text, key, size, x + w / 2, ty); ty += size + 10


def _postmark(sh: Sheet, cx, cy, ring: str, center: str, r=120):
    col = (58, 58, 96)
    for k_ in range(4):
        yy = cy - 42 + k_ * 28
        sh.line([(cx - r - 20 - t * 11, yy + 7 * math.sin(t / 2.2)) for t in range(26)], col, 4)
    sh.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAPER, outline=col, width=6)
    sh.ellipse([cx - r + 44, cy - r + 44, cx + r - 44, cy + r - 44], outline=col, width=3)
    for i, ch in enumerate(ring):
        a = math.radians(-90 + i * 360 / max(1, len(ring)))
        sh.glyph(cx + (r - 24) * math.cos(a), cy + (r - 24) * math.sin(a), ch, "mono_b", 20, col, math.degrees(a) + 90)
    if center:
        sh.centered(center, "mono_b", 26, cx, cy - 15, fill=col)


def _draw_header(sh: Sheet, project, settings, n, total, board_scenes, n_shots, header_h):
    _airmail_edge(sh, 0); _airmail_edge(sh, header_h - 40)
    box_y, box_h = (62, 250) if settings.get("tagline") else (70, 250)
    rng = f"SCENES {board_scenes[0]} – {board_scenes[-1]}" if len(board_scenes) > 1 else \
        (f"SCENE {board_scenes[0]}" if board_scenes else "SCENES")
    subtitle = settings.get("subtitle") or ""
    _boxed(sh, M, box_y, 420, box_h, [(f"BOARD {n}", "serif_b", 44), (f"of {total}", "pal", 30)])
    _boxed(sh, M + 450, box_y, 720, box_h, [(rng, "serif_b", 44)] + ([(subtitle, "pal_b", 32)] if subtitle else []) +
           [(f"{n_shots} shots · {len(board_scenes)} scenes", "pal", 30)])
    period = settings.get("period") or project.get("period") or ""
    _boxed(sh, DESIGN_W - M - 1560, box_y, 520, box_h, [("PERIOD", "pal_b", 32), (period or "—", "serif_b", 44)])
    _boxed(sh, DESIGN_W - M - 1010, box_y, 290, box_h, [("PAGE", "pal_b", 32), (f"{n} of {total}", "serif_b", 44)])
    _postmark(sh, DESIGN_W - M - 140, box_y + box_h // 2,
              settings.get("postmark_ring") or (" · ".join([project.get("title", "").upper()[:18], "AIR MAIL", ""])),
              settings.get("postmark_center") or _year(period))

    title = settings.get("title_native") or settings.get("title") or (project.get("title") or "").upper()
    if is_complex_script(title):
        size = 128
        while (lambda b: b[2] - b[0])(shaped_bbox(title, "native_b", size)) > 1780 and size > 80:
            size -= 4
        sh.centered(title, "serif_b", size, DESIGN_W / 2, 58)
    else:
        size = 150
        while text_width(title, "serif_b", size) > 1780 and size > 80:
            size -= 6
        sh.centered(title, "serif_b", size, DESIGN_W / 2, 50)
    if settings.get("title_sub"):
        sh.centered(settings["title_sub"], "hand", 42, DESIGN_W / 2, 232, fill=MAROON)

    tagline = settings.get("tagline")
    if tagline:
        ty, size = 352, 76
        key = "native_b" if is_complex_script(tagline) else "serif_b"
        if is_complex_script(tagline):
            l, t, r, b = shaped_bbox(tagline, key, size)
            tw, th = r - l, b - t
        else:
            tw, th = text_width(tagline, key, size), size
        sh.centered(tagline, key, size, DESIGN_W / 2, ty, fill=MAROON)
        ym = ty + th / 2
        for side in (-1, 1):
            x_in = DESIGN_W / 2 + side * (tw / 2 + 40)
            x_out = DESIGN_W / 2 + side * (DESIGN_W / 2 - M - 40)
            sh.line([(x_in, ym), (x_out, ym)], MAROON, 3)
            sh.line([(x_in + side * 20, ym + 12), (x_out, ym + 12)], (190, 150, 140), 1)
            sh.poly([(x_in, ym), (x_in + side * 16, ym - 10), (x_in + side * 32, ym), (x_in + side * 16, ym + 10)], MAROON)
        if settings.get("tagline_translation"):
            sh.centered(settings["tagline_translation"], "serif_i", 36, DESIGN_W / 2, ty + th + 34, fill=MUTED)


def _draw_row(sh: Sheet, row, y, project, settings, color_of):
    segs = []
    for i, it in enumerate(row):
        sc = it[1]["scene_number"] if it[0] == "shot" else None
        if segs and segs[-1][0] == sc:
            segs[-1][2] = i
        else:
            segs.append([sc, i, i, it[1] if it[0] == "shot" else None, it[3] if it[0] == "shot" else False])
    for sc, a, b, scene, cont in segs:
        if sc is None:
            continue
        x0 = M + a * (PW + GAP); x1 = M + b * (PW + GAP) + PW
        sh.rect([x0, y, x1, y + STRIP_H], fill=color_of[sc])
        title = scene_title(scene) + ("  (CONT.)" if cont else "")
        if text_width(title, "serif_b", 34) > x1 - x0 - 30:
            title = f"SCENE {sc}" + (" (CONT.)" if cont else "")
        sh.text(x0 + 20, y + 13, title, "serif_b", 34, fill=(255, 255, 255))
    py = y + STRIP_H + 14
    for i, it in enumerate(row):
        x = M + i * (PW + GAP)
        if it[0] == "shot":
            _draw_panel(sh, x, py, it[1], it[2])
        elif it[0] == "cast":
            _draw_cast_card(sh, x, py, project.get("characters") or [], settings)
        elif it[0] == "end":
            _draw_end_card(sh, x, py, DESIGN_W - M - x, project, settings)


def _draw_panel(sh: Sheet, x, y, scene, shot):
    path = shot.get("image_path")
    if path and os.path.exists(path):
        with Image.open(path) as im:
            size = im.size
        sh.image(path, cover_crop(size, shot.get("crop"), PW / IH), [x, y, x + PW, y + IH])
    else:
        sh.rect([x, y, x + PW, y + IH], fill=(210, 206, 198))
        sh.centered("NO IMAGE YET", "sans_b", 26, x + PW / 2, y + IH / 2 - 14, fill=MUTED)
    sh.rect([x, y, x + PW, y + PH], outline=INK, width=4)
    sh.rect([x, y + IH, x + PW, y + PH], fill=CAPTION_BG, outline=INK, width=4)
    num = f"{scene['scene_number']}.{shot['shot_number']}"
    bw = text_width(num, "sans_b", 26) + 26
    sh.rect([x, y, x + bw, y + 44], fill=MAROON); sh.text(x + 13, y + 8, num, "sans_b", 26, fill=(255, 255, 255))
    tag = shot_tag(shot.get("shot_size"))
    tw = text_width(tag, "sans_b", 22) + 28
    sh.rect([x + bw + 10, y + 8, x + bw + 10 + tw, y + 40], fill=YELLOW, outline=INK, width=2)
    sh.text(x + bw + 24, y + 12, tag, "sans_b", 22)
    act = _wrap(shot.get("caption") or "", "serif", 25, PW - 28)[:2]
    dia = _wrap(shot.get("dialogue") or "", "serif_i", 24, PW - 28)
    if len(act) + len(dia) > 3:
        act = act[:max(1, 3 - len(dia))]; dia = dia[:3 - len(act)]
    ty = y + IH + 12
    for line in act:
        sh.text(x + 14, ty, line, "serif", 25); ty += 32
    for line in dia:
        sh.text(x + 14, ty, line, "serif_i", 24, fill=MAROON); ty += 31
    my = y + PH - 36
    sh.text(x + 14, my, "Lens:", "sans_b", 21, fill=MUTED); sh.text(x + 76, my, shot.get("lens") or "—", "sans", 21)
    mx = x + PW // 2 - 10
    sh.text(mx, my, "Movement:", "sans_b", 21, fill=MUTED)
    sh.text(mx + 116, my, _fit(shot.get("movement") or "Static", "sans", 21, x + PW - mx - 128), "sans", 21)


def _mtime(path: str) -> int:
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return 0


def _face_crop(path: str) -> Optional[Tuple[int, int, int, int]]:
    return _face_crop_cached(path, _mtime(path))


@lru_cache(maxsize=256)
def _face_crop_cached(path: str, mtime: int) -> Optional[Tuple[int, int, int, int]]:
    try:
        from app import face_identity
        faces = face_identity.detect_faces(path, min_width_frac=0.0)
    except Exception:
        faces = []
    with Image.open(path) as im:
        W, H = im.size
    if not faces:
        return None
    f = faces[0]
    side = min(max(f["w"], f["h"]) * 2.1, W, H)
    cx, cy = f["x"] + f["w"] / 2, f["y"] + f["h"] * 0.5
    l = max(0, min(cx - side / 2, W - side)); t = max(0, min(cy - side / 2, H - side))
    return int(l), int(t), int(l + side), int(t + side)


def _best_ref(paths: Sequence[str]) -> Optional[str]:
    return _best_ref_cached(tuple(paths), tuple(_mtime(p) for p in paths))


@lru_cache(maxsize=128)
def _best_ref_cached(paths: Tuple[str, ...], mtimes: Tuple[int, ...]) -> Optional[str]:
    """The reference whose detected face is largest (a frontal or head-and-shoulders portrait)."""
    best, best_area = None, -1
    for p in paths:
        try:
            from app import face_identity
            faces = face_identity.detect_faces(p, min_width_frac=0.0)
        except Exception:
            faces = []
        area = faces[0]["w"] * faces[0]["h"] if faces else 0
        if area > best_area:
            best, best_area = p, area
    return best


def _draw_cast_card(sh: Sheet, x, y, characters, settings):
    sh.rect([x, y, x + PW, y + PH], fill=CAPTION_BG, outline=INK, width=4)
    sh.rect([x, y, x + PW, y + 50], fill=INK)
    sh.centered("CAST LOCK", "sans_b", 24, x + PW / 2, y + 12, fill=(255, 255, 255))
    chars = [dict(c, ref_path=_best_ref(c.get("ref_paths") or [])) for c in characters][:2]
    chars = [c for c in chars if c["ref_path"]]
    if chars:
        cw = (PW - 14 * (len(chars) + 1)) // len(chars)
        ch_h = IH - 30
        for i, ch in enumerate(chars):
            path = ch["ref_path"]
            with Image.open(path) as im:
                size = im.size
            crop = cover_crop(size, _face_crop(path), cw / ch_h)
            px = x + 14 + i * (cw + 14)
            sh.image(path, crop, [px, y + 64, px + cw, y + 64 + ch_h])
            sh.rect([px, y + 64, px + cw, y + 64 + ch_h], outline=INK, width=2)
            sh.centered(ch["name"], "sans_b", 21, px + cw / 2, y + IH + 44)
    notes = settings.get("cast_notes") or [f"{c['name']}: {c.get('note', '')}".strip(": ") for c in chars]
    ty = y + IH + 80
    for line in notes[:2]:
        sh.text(x + 14, ty, _fit(line, "sans", 19, PW - 28), "sans", 19); ty += 26


def _draw_end_card(sh: Sheet, x, y, w, project, settings):
    sh.rect([x, y, x + w, y + PH], fill=(30, 28, 34), outline=INK, width=4)
    for i, xx in enumerate(range(int(x) + 10, int(x + w) - 30, 44)):
        col = RED if i % 2 == 0 else BLUE
        sh.poly([(xx, y + 30), (xx + 20, y + 10), (xx + 42, y + 10), (xx + 22, y + 30)], col)
        sh.poly([(xx, y + PH - 10), (xx + 20, y + PH - 30), (xx + 42, y + PH - 30), (xx + 22, y + PH - 10)], col)
    cream, gold, soft = (244, 232, 205), (226, 190, 128), (200, 188, 170)
    cx = x + w / 2
    lines = settings.get("end_lines") or []
    if lines:
        size = 56
        native = any(is_complex_script(l) for l in lines)
        key = "native_b" if native else "serif_b"
        width_of = (lambda t: (lambda b: b[2] - b[0])(shaped_bbox(t, key, size))) if native else \
            (lambda t: text_width(t, key, size))
        while max(width_of(t) for t in lines) > w - 200 and size > 30:
            size -= 2
        ty = y + 70
        for t in lines:
            ty += sh.centered(t, key, size, cx, ty, fill=cream) + (20 if native else 14)
        if settings.get("end_translation"):
            sh.centered(settings["end_translation"], "serif_i", 30, cx, ty + 2, fill=soft)
    else:
        title = settings.get("title_native") or settings.get("title") or (project.get("title") or "").upper()
        sh.centered(title, "serif_b", 96, cx, y + PH / 2 - 150, fill=cream)
    sig = settings.get("signature")
    if sig:
        key = "native" if is_complex_script(sig) else "hand"
        if is_complex_script(sig):
            l, t, r, b = shaped_bbox(sig, key, 52)
            sw, shh = r - l, b - t
        else:
            sw, shh = text_width(sig, key, 52), 52
        sx, sy = x + w - 70 - sw, y + PH - 170
        if is_complex_script(sig):
            sh.shaped(sx, sy, sig, key, 52, gold)
        else:
            sh.text(sx, sy, sig, key, 52, fill=gold)
        sh.line([(sx, sy + shh + 12), (x + w - 70, sy + shh + 12)], gold, 2)
        if settings.get("signature_roman"):
            rom = "— " + settings["signature_roman"]
            sh.text(x + w - 70 - text_width(rom, "hand", 30), sy + shh + 20, rom, "hand", 30, fill=soft)
    sh.text(x + 70, y + PH - 100, settings.get("end_stamp") or "END OF BOARD  ·  TO BE CONTINUED", "mono_b", 26,
            fill=(160, 150, 138))


def _icon(sh: Sheet, kind, cx, cy):
    col = INK
    if kind == "camera_style":
        sh.rect([cx, cy, cx + 70, cy + 48], outline=col, width=5)
        sh.ellipse([cx + 20, cy + 9, cx + 50, cy + 39], outline=col, width=5); sh.rect([cx + 10, cy - 10, cx + 30, cy], fill=col)
    elif kind == "colour_tone":
        sh.ellipse([cx, cy - 6, cx + 70, cy + 54], outline=col, width=5)
        for j, c in enumerate([RED, YELLOW, BLUE, (40, 140, 90)]):
            sh.ellipse([cx + 12 + j * 13, cy + 8 + (j % 2) * 16, cx + 26 + j * 13, cy + 22 + (j % 2) * 16], fill=c)
    elif kind == "lighting":
        sh.ellipse([cx + 10, cy - 8, cx + 60, cy + 40], outline=col, width=5); sh.rect([cx + 24, cy + 40, cx + 46, cy + 56], outline=col, width=4)
    elif kind == "mood":
        sh.ellipse([cx, cy - 8, cx + 64, cy + 56], outline=col, width=5)
        sh.ellipse([cx + 18, cy + 12, cx + 26, cy + 20], fill=col); sh.ellipse([cx + 38, cy + 12, cx + 46, cy + 20], fill=col)
        sh.arc([cx + 14, cy + 14, cx + 50, cy + 44], 20, 160, col, 5)
    elif kind == "lens_guide":
        sh.ellipse([cx, cy - 8, cx + 64, cy + 56], outline=col, width=5); sh.ellipse([cx + 16, cy + 8, cx + 48, cy + 40], outline=col, width=4)
    else:
        sh.rect([cx + 6, cy - 8, cx + 58, cy + 56], outline=col, width=5)
        for j in range(3):
            sh.line([(cx + 16, cy + 8 + j * 14), (cx + 48, cy + 8 + j * 14)], col, 4)


LEGEND_ORDER = [("camera_style", "CAMERA STYLE"), ("colour_tone", "COLOUR TONE"), ("lighting", "LIGHTING"),
                ("mood", "MOOD"), ("lens_guide", "LENS GUIDE"), ("notes", "NOTES")]


def _draw_footer(sh: Sheet, H, legend, settings, project, n, total):
    fy = H - FOOTER_H - M + 20
    sh.rect([M, fy, DESIGN_W - M, H - M], fill=(252, 248, 238), outline=INK, width=4)
    cw = (DESIGN_W - 2 * M) // len(LEGEND_ORDER)
    for i, (key, head) in enumerate(LEGEND_ORDER):
        cx = M + i * cw + 40; cy = fy + 70
        _icon(sh, key, cx, cy)
        tx = cx + 96
        sh.text(tx, fy + 40, head, "sans_b", 34, fill=MAROON)
        for j, line in enumerate((legend.get(key) or [])[:3]):
            sh.text(tx, fy + 92 + j * 42, _fit(line, "sans", 30, cw - 150), "sans", 30)
        if i:
            sh.line([(M + i * cw, fy + 30), (M + i * cw, fy + FOOTER_H - 80)], (200, 190, 175), 2)
    names = " & ".join(c["name"] for c in (project.get("characters") or []) if c.get("ref_paths"))
    credit = settings.get("credit") or "  ·  ".join(filter(None, [
        (settings.get("title_roman") or settings.get("title") or project.get("title") or "").upper(),
        "STORYBOARD", "GENERATED WITH 70MM.AI", f"CHARACTER-LOCKED: {names}" if names else ""]))
    sh.centered(credit, "mono_b", 20, DESIGN_W / 2, H - M - 60, fill=MUTED)


# ── public API ──────────────────────────────────────────────────────────────
def _fingerprint(project: Dict[str, Any], settings: Dict[str, Any]) -> str:
    """Hash of EVERYTHING that affects the sheets: text, captions, crops, shot
    data, settings, and the size + mtime of every image used (a regenerated
    shot or re-locked character changes it), plus ENGINE_VERSION."""
    files = []
    for sc in project.get("scenes", []):
        files += [sh.get("image_path") for sh in sc.get("shots", [])]
    for c in project.get("characters", []):
        files += list(c.get("ref_paths") or [])
    stats = {}
    for f in files:
        if f:
            try:
                st = os.stat(f)
                stats[f] = [st.st_size, st.st_mtime_ns]
            except OSError:
                stats[f] = None
    blob = json.dumps({"v": ENGINE_VERSION, "project": project, "settings": settings, "files": stats},
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def preview_path_for(png_path: str) -> str:
    return png_path[:-4] + "_preview.jpg"


def _render_outputs(sheet: Sheet, png_path: str, pdf_path: str) -> None:
    """PNG (+ preview) and PDF in parallel threads -- zlib and Pillow's
    resampling release the GIL, so the two overlap almost completely."""
    def png_job():
        img = _render_png(sheet)
        img.save(png_path, "PNG", compress_level=PNG_COMPRESS_LEVEL)
        preview = img.resize((PREVIEW_WIDTH, round(img.height * PREVIEW_WIDTH / img.width)), Image.LANCZOS)
        preview.save(preview_path_for(png_path), "JPEG", quality=88, optimize=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(png_job), pool.submit(_render_pdf, sheet, pdf_path)]
        for f in futures:
            f.result()


def compose_project_boards(project: Dict[str, Any], settings: Dict[str, Any], filename_base: str,
                           out_dir: str = BOARDS_DIR, force: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
    """Render every board sheet for a project as PNG (7200 px) + vector PDF.

    `project`: {"title", "period", "characters": [{"name", "ref_paths", "note"}],
                "scenes": [{"scene_number", "heading", "shots": [{"shot_number",
                "shot_size", "lens", "movement", "lighting", "emotion",
                "color_palette", "caption", "dialogue", "crop", "image_path"}]}]}
    Returns (boards, cached). boards: [{"board_number", "total", "scene_range",
    "shot_count", "png_path", "pdf_path", "preview_path"}]. When nothing that
    affects the sheets has changed since the last compose (same fingerprint and
    all files present), the previous files are returned without re-rendering.
    """
    os.makedirs(out_dir, exist_ok=True)
    settings = settings or {}
    manifest_path = os.path.join(out_dir, f"{filename_base}_boards.json")
    fp = _fingerprint(project, settings)
    if not force and os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, encoding="utf-8"))
            boards = manifest.get("boards") or []
            if manifest.get("fingerprint") == fp and boards and all(
                    os.path.exists(b[k]) for b in boards for k in ("png_path", "pdf_path", "preview_path")):
                return boards, True
        except (OSError, ValueError):
            pass

    results = []
    for b in build_sheets(project, settings):
        stem = f"{filename_base}_board_{b['board_number']}"
        png_path = os.path.join(out_dir, f"{stem}.png")
        pdf_path = os.path.join(out_dir, f"{stem}.pdf")
        _render_outputs(b["sheet"], png_path, pdf_path)
        results.append({k: v for k, v in b.items() if k != "sheet"} |
                       {"png_path": png_path, "pdf_path": pdf_path, "preview_path": preview_path_for(png_path),
                        "scene_range": list(b["scene_range"])})
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": fp, "engine": ENGINE_VERSION, "boards": results}, f, indent=1)
    return results, False
