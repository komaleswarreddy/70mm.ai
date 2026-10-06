"""Stage 7 face identity helpers: find each character's face in a composed
frame so the identity pass can repaint THAT face from THAT character's
references.

Why this exists. The previous identity pass conditioned the whole frame on a
single "focal" character, which left two measured defects:
  - in two-character shots the other character got no identity conditioning
    at all and drifted (SITA read as a different actress across shots);
  - a whole-frame pass has to stay at low denoise (0.40) or it wrecks the
    composition, which capped how far a face could be pulled toward its
    reference -- RAM's faces matched RAM barely better than ANWAR.

Detection is OpenCV YuNet (MIT) and recognition is OpenCV SFace (Apache-2.0),
both run locally from backend/models/opencv/. They replace MediaPipe for this
job because MediaPipe's landmarker returns nothing for a profile face, which
silently skipped identity on exactly the angled shots that need it; YuNet
detected every locked reference angle, profiles included. Neither model is a
research-licensed face-ID net (InsightFace/ArcFace were avoided for that).

Every function degrades to "no faces" if the models are missing, so the caller
falls back to the whole-frame pass rather than failing a generation.
"""
import io
import itertools
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
MODEL_DIR = os.path.join(BACKEND_ROOT, "models", "opencv")
YUNET_MODEL = os.path.join(MODEL_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_MODEL = os.path.join(MODEL_DIR, "face_recognition_sface_2021dec.onnx")

# Faces narrower than this fraction of the frame are background extras (train
# passengers, distant soldiers); repainting them as a lead character would be
# wrong, and attributing them skewed the audit with near-zero scores.
MIN_FACE_WIDTH_FRAC = 0.04
DETECTION_SCORE = 0.6

# Crop side = face size * this, so the repaint sees hair, ears and jaw line --
# the parts that make a face read as a specific person -- plus enough context
# to blend.
CROP_SCALE = 2.2
CROP_WORK_SIZE = 768


class FaceBox(dict):
    """{"x","y","w","h","score","feature"} in pixel space of the source frame."""


@lru_cache(maxsize=1)
def _models():
    try:
        import cv2
        if not (os.path.exists(YUNET_MODEL) and os.path.exists(SFACE_MODEL)):
            logger.warning(f"Face identity models missing in {MODEL_DIR} -- per-face identity disabled.")
            return None
        det = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (320, 320),
                                        score_threshold=DETECTION_SCORE, nms_threshold=0.3, top_k=20)
        rec = cv2.FaceRecognizerSF.create(SFACE_MODEL, "")
        return det, rec
    except Exception as e:
        logger.warning(f"Face identity models failed to load ({e}) -- per-face identity disabled.")
        return None


def is_available() -> bool:
    return _models() is not None


def _to_bgr(image) -> Optional[np.ndarray]:
    import cv2
    if isinstance(image, (bytes, bytearray)):
        return cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    if isinstance(image, Image.Image):
        return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    return cv2.imread(str(image))


def detect_faces(image, min_width_frac: float = MIN_FACE_WIDTH_FRAC) -> List[FaceBox]:
    """Faces in `image` (path, bytes or PIL), largest first, each with an
    L2-normalised SFace feature."""
    models = _models()
    img = _to_bgr(image) if models else None
    if img is None:
        return []
    det, rec = models
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, found = det.detect(img)
    out: List[FaceBox] = []
    for f in (found if found is not None else []):
        if f[2] < w * min_width_frac:
            continue
        feat = rec.feature(rec.alignCrop(img, f)).flatten()
        out.append(FaceBox(x=int(f[0]), y=int(f[1]), w=int(f[2]), h=int(f[3]),
                           score=float(f[14]), feature=feat / np.linalg.norm(feat)))
    out.sort(key=lambda b: -b["w"] * b["h"])
    return out


def resolve_local_path(p: str) -> str:
    """A stored reference URL ("/static/character_refs/x.png") -> file on disk.

    Checked against the backend root FIRST: on Windows os.path.isabs() is True
    for "/static/...", so treating a leading slash as "absolute" resolved to
    C:\\static\\... and silently found no references -- per-face identity then
    could not tell RAM's face from SITA's.
    """
    under_backend = os.path.join(BACKEND_ROOT, p.lstrip("/\\"))
    return under_backend if os.path.exists(under_backend) else p


def reference_features(paths: Sequence[str]) -> List[np.ndarray]:
    """SFace features for a character's locked reference images (largest face each)."""
    feats = []
    for p in paths:
        disk = resolve_local_path(p)
        faces = detect_faces(disk, min_width_frac=0.0)
        if faces:
            feats.append(faces[0]["feature"])
    return feats


def identity_similarity(feature: np.ndarray, refs: Sequence[np.ndarray]) -> float:
    """Mean SFace cosine to a reference set (OpenCV's same-person threshold is 0.363)."""
    if not refs:
        return 0.0
    return float(np.mean([float(np.dot(feature, r)) for r in refs]))


def assign_faces(faces: Sequence[FaceBox], character_refs: Dict[str, Sequence[np.ndarray]],
                 priority: Sequence[str]) -> List[Tuple[str, FaceBox]]:
    """Which detected face belongs to which character.

    Exhaustive over assignments (at most a handful of faces x characters), so
    two characters can never both claim the best-matching face. Freshly
    composed faces carry little identity yet, so similarity alone is a weak
    signal; ties go to the largest faces, and when there are more characters
    than faces the `priority` order (focal character first) decides who gets
    repainted.
    """
    names = [n for n in priority if n in character_refs] or list(character_refs)
    faces = list(faces)[: max(len(names), 1) + 2]
    if not faces or not names:
        return []
    k = min(len(faces), len(names))
    best, best_score = [], -1e9
    for chosen_names in itertools.combinations(names, k):
        for chosen_faces in itertools.permutations(range(len(faces)), k):
            score = 0.0
            for n, fi in zip(chosen_names, chosen_faces):
                score += identity_similarity(faces[fi]["feature"], character_refs[n])
                score += 0.02 * (len(faces) - fi)          # prefer larger faces on near-ties
                score += 0.03 * (len(names) - names.index(n))  # prefer focal character
            if score > best_score:
                best_score, best = score, list(zip(chosen_names, chosen_faces))
    return [(n, faces[fi]) for n, fi in best]


def identity_scores(image, character_refs: Dict[str, Sequence[np.ndarray]],
                    priority: Sequence[str]) -> Dict[str, float]:
    """SFace similarity of each character's assigned face to its references."""
    faces = detect_faces(image)
    return {name: identity_similarity(face["feature"], character_refs[name])
            for name, face in assign_faces(faces, character_refs, priority)}


def crop_box(face: FaceBox, frame_w: int, frame_h: int, scale: float = CROP_SCALE) -> Tuple[int, int, int, int]:
    """Square crop around a face, clamped inside the frame."""
    side = int(min(max(face["w"], face["h"]) * scale, frame_w, frame_h))
    cx = face["x"] + face["w"] / 2
    cy = face["y"] + face["h"] * 0.45  # a touch above centre keeps the hair in frame
    left = int(max(0, min(cx - side / 2, frame_w - side)))
    top = int(max(0, min(cy - side / 2, frame_h - side)))
    return left, top, left + side, top + side


def head_mask(face: FaceBox, box: Tuple[int, int, int, int], size: int = CROP_WORK_SIZE,
              feather: int = 24) -> Image.Image:
    """White ellipse over head+hair inside the crop, feathered, at work size."""
    left, top, right, bottom = box
    s = size / (right - left)
    fx, fy, fw, fh = (face["x"] - left) * s, (face["y"] - top) * s, face["w"] * s, face["h"] * s
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([fx - fw * 0.30, fy - fh * 0.55, fx + fw * 1.30, fy + fh * 1.20], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather))


def extract_crop(frame: Image.Image, box: Tuple[int, int, int, int], size: int = CROP_WORK_SIZE) -> Image.Image:
    return frame.crop(box).convert("RGB").resize((size, size), Image.LANCZOS)


def paste_crop(frame: Image.Image, repainted: Image.Image, box: Tuple[int, int, int, int],
               mask: Image.Image) -> Image.Image:
    """Blend the repainted crop back through the feathered head mask only,
    so nothing outside the head can change."""
    left, top, right, bottom = box
    side = right - left
    patch = repainted.convert("RGB").resize((side, side), Image.LANCZOS)
    alpha = mask.resize((side, side), Image.LANCZOS)
    out = frame.convert("RGB").copy()
    out.paste(patch, (left, top), alpha)
    return out


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
