"""
Stage 9 — visual continuity QA.

Three checks per spec, all self-hosted/free:
1. Character identity: CLIP cosine similarity between a generated shot and
   each present character's locked reference embedding. Deliberately NOT a
   face-specific model — same licensing decision as Stage 6 (no
   InsightFace/IP-Adapter-FaceID/InstantID).
2. Costume/style/location drift: the SAME CLIP embedding, compared against
   the scene's other shots (spec's separate "CLIP embedding comparison"
   bullet — same model, different comparison target, so there's exactly
   one embedding technology to maintain across Stages 6 and 9).
3. Lighting/color-grade consistency: an OpenCV color-histogram comparison
   within the scene, exactly as the spec names.

Any shot below threshold is flagged needs_review and, only if the caller
opts in, queued for ONE reinforced-conditioning regeneration attempt —
never automatically/silently, since a "check" endpoint triggering an
expensive regeneration by default would be surprising API behavior.
"""
import os
import logging
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.embedding_service import compute_image_embedding, cosine_similarity

logger = logging.getLogger(__name__)

# Spec: "start at cosine >= 0.55, tune empirically."
IDENTITY_SIMILARITY_THRESHOLD = 0.55
# No spec-given default for these two — chosen conservatively, meant to be tuned.
STYLE_DRIFT_THRESHOLD = 0.5
# Even L1-normalized chi-square (HISTCMP_CHISQR) turned out to be too
# sensitive to near-zero bins in a fine-grained 8x8x8=512-bin histogram
# of real photographic images -- live-measured distances among 8 shots
# from a single genuinely-coherent, verified-good real generation run
# ranged from 1.1 to 18434, useless as a threshold target. Switched to
# HISTCMP_BHATTACHARYYA instead (0 = identical, 1 = maximally different,
# bounded -- specifically designed to avoid chi-square's near-zero-bin
# blowup). Re-measured the same 8 known-good shots against each other
# under Bhattacharyya: 0.38-0.92, median 0.77 -- i.e. even correctly-
# generated shots of the same scene vary a lot by raw color histogram
# once composition/framing differs shot-to-shot. Threshold set just
# above that observed good-data ceiling so none of them false-flag,
# while still catching a genuinely severe outlier beyond that range.
COLOR_HISTOGRAM_DISTANCE_THRESHOLD = 0.93

STATIC_ROOT = os.path.dirname(os.path.dirname(__file__))


def _resolve_disk_path(image_url: Optional[str]) -> Optional[str]:
    if not image_url:
        return None
    disk_path = image_url.lstrip("/")
    full_path = os.path.join(STATIC_ROOT, disk_path)
    return full_path if os.path.exists(full_path) else None


def compute_color_histogram(image_path: str) -> Optional[np.ndarray]:
    """Normalized per-channel color histogram via OpenCV, exactly as the
    spec names for lighting/color-grade consistency checks."""
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"Could not read image for histogram comparison: {image_path}")
        return None
    hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    # NORM_L1 (bins sum to 1), not the default NORM_L2 -- verified live: L2
    # normalization leaves many bins near-zero, and HISTCMP_CHISQR divides
    # by each H1(i), so near-zero denominators blew distances up into the
    # thousands even between genuinely-coherent same-scene shots (flagging
    # 8/8 real generated images as continuity failures). L1 is the textbook
    # normalization chi-square distance is actually designed for.
    cv2.normalize(hist, hist, norm_type=cv2.NORM_L1)
    return hist


def histogram_distance(hist_a: np.ndarray, hist_b: np.ndarray) -> float:
    """Bhattacharyya distance -- 0 = identical, 1 = maximally different,
    bounded (unlike chi-square, which isn't -- see the threshold comment
    above for why this is the one actually in use)."""
    return float(cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_BHATTACHARYYA))


def check_shot_continuity(
    shot_image_url: Optional[str],
    character_embeddings: List[Dict[str, Any]],
    scene_other_image_urls: List[str],
) -> Dict[str, Any]:
    """
    `character_embeddings`: [{"name", "embedding_vector": List[float] | None}]
    for every named character present in this shot.
    `scene_other_image_urls`: image_urls of the scene's OTHER completed
    shots (for the style-drift and color-grade comparisons).

    Returns {"needs_review": bool, "flags": [...], "identity_score": float|None, "color_distance": float|None}.
    """
    flags: List[str] = []
    identity_score: Optional[float] = None
    color_distance: Optional[float] = None

    shot_path = _resolve_disk_path(shot_image_url)
    if not shot_path:
        return {"needs_review": False, "flags": ["No image to check yet."], "identity_score": None, "color_distance": None}

    shot_embedding = compute_image_embedding(shot_path)

    # 1. Character identity
    for char in character_embeddings:
        if not char.get("embedding_vector"):
            continue
        score = cosine_similarity(shot_embedding, char["embedding_vector"]) if shot_embedding else 0.0
        identity_score = score if identity_score is None else min(identity_score, score)
        if score < IDENTITY_SIMILARITY_THRESHOLD:
            flags.append(f"Character '{char['name']}' identity similarity {score:.2f} is below threshold {IDENTITY_SIMILARITY_THRESHOLD}.")

    other_paths = [p for p in (_resolve_disk_path(u) for u in scene_other_image_urls) if p]

    # 2. Style/costume/location drift vs. the rest of the scene.
    if shot_embedding and other_paths:
        other_embeddings = [e for e in (compute_image_embedding(p) for p in other_paths) if e]
        if other_embeddings:
            avg_sim = sum(cosine_similarity(shot_embedding, e) for e in other_embeddings) / len(other_embeddings)
            if avg_sim < STYLE_DRIFT_THRESHOLD:
                flags.append(f"Visual style drifted from the rest of the scene (avg similarity {avg_sim:.2f}).")

    # 3. Color/lighting grade consistency within the scene.
    shot_hist = compute_color_histogram(shot_path)
    if shot_hist is not None and other_paths:
        other_hists = [h for h in (compute_color_histogram(p) for p in other_paths) if h is not None]
        if other_hists:
            avg_dist = sum(histogram_distance(shot_hist, h) for h in other_hists) / len(other_hists)
            color_distance = avg_dist
            if avg_dist > COLOR_HISTOGRAM_DISTANCE_THRESHOLD:
                flags.append(f"Color/lighting grade diverges from the rest of the scene (distance {avg_dist:.2f}).")

    return {
        "needs_review": bool(flags),
        "flags": flags,
        "identity_score": identity_score,
        "color_distance": color_distance,
    }

# ── Face presence check (Stage 7 two-shot verification) ────────────────────
# Not a continuity metric -- a generation-correctness gate. USO reference
# conditioning reproduces its reference's single-subject structure, so a shot
# that should show two characters together reliably came back with only the
# focal one in frame (live-observed on a Two-Shot and a "show both" medium
# shot, both of which rendered one person despite the prompt naming two).
# Counting faces is what lets Stage 7 detect that and retry.
_FACE_CASCADES = None


def _load_face_cascades():
    global _FACE_CASCADES
    if _FACE_CASCADES is None:
        base = cv2.data.haarcascades
        _FACE_CASCADES = (
            cv2.CascadeClassifier(os.path.join(base, "haarcascade_frontalface_default.xml")),
            cv2.CascadeClassifier(os.path.join(base, "haarcascade_profileface.xml")),
        )
    return _FACE_CASCADES


def _box_iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    return inter / float(aw * ah + bw * bh - inter)


def count_faces(image_path: str) -> int:
    """Rough count of distinct faces in a generated shot.

    Deliberately conservative and cheap (OpenCV Haar, already a dependency --
    no face-recognition model, same licensing reasoning as embedding_service).

    Overlapping detections MUST be merged: the profile cascade fires a second
    time on a face the frontal cascade already found, which made a naive
    frontal+profile sum report 2 faces for a verified single-subject image.
    The profile cascade only detects one facing direction, so the mirrored
    image is checked too.

    Known limitation: this counts faces, it cannot identify them -- background
    extras in a crowd scene can satisfy a ">= 2" check even if the intended
    second character is absent. It reliably catches the actual failure mode
    seen in practice (a lone reference-shaped portrait with nobody else in
    frame), which is what it is used for.
    """
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"count_faces: could not read {image_path}")
        return 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    frontal, profile = _load_face_cascades()

    boxes = list(frontal.detectMultiScale(gray, 1.1, 5, minSize=(40, 40)))
    boxes += list(profile.detectMultiScale(gray, 1.1, 5, minSize=(40, 40)))
    flipped = cv2.flip(gray, 1)
    width = gray.shape[1]
    boxes += [
        (width - x - w, y, w, h)
        for (x, y, w, h) in profile.detectMultiScale(flipped, 1.1, 5, minSize=(40, 40))
    ]

    kept = []
    for box in sorted(boxes, key=lambda t: -t[2] * t[3]):
        if all(_box_iou(box, k) < 0.25 for k in kept):
            kept.append(box)
    return len(kept)
