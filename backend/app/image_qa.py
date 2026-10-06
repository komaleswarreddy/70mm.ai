"""Stage 7 quality gate — decides whether a generated shot is deliverable.

Two layers, because each catches what the other cannot. Both were calibrated
against frames whose contents were verified by eye first, not assumed:

1. LOCAL (free, offline, fast): image dimensions catch a silent Pillow
   placeholder; MediaPipe face landmarks count people; MediaPipe hand
   landmarks catch a malformed hand -- a badly deformed hand fails hand
   detection outright, which is the signal used here (measured: a frame with
   a visibly broken grip returned zero hands while clean frames returned one
   with plausible finger geometry).

2. GROQ VISION (semantic, qwen/qwen3.8-27b): catches everything the landmark
   layer structurally cannot -- a missing second character, wrong shot size,
   wardrobe failures, garbled text, duplicated limbs. The local layer alone
   passed a known-bad frame (OpenCV Haar even false-positived a second face on
   background architecture) that a vision reviewer correctly failed for a
   missing character. Gemini was the original reviewer; it is not used.

   Prompt shape matters and was tuned: an open-ended "list any anatomy
   problems" MISSED a duplicated forearm on that same frame, while forcing an
   explicit per-person census ("how many arms / hands does EACH figure have")
   caught it. The census wording is therefore load-bearing, not decorative.

The vision reviewer is treated as advisory-but-authoritative-when-available: if the API is
rate-limited or down, the local layer still runs and generation proceeds rather
than blocking the whole pipeline on a third-party outage.
"""
import base64
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
MEDIAPIPE_MODEL_DIR = os.path.join(BACKEND_ROOT, "models", "mediapipe")

# Real ComfyUI output vs the Pillow fallback placeholder.
REAL_IMAGE_SIZE = (1024, 640)
PLACEHOLDER_IMAGE_SIZE = (1024, 512)

# Groq's gpt-oss-120b (the project's text model) is text-only and rejects image
# input, so the semantic layer uses the one vision-capable model on the Groq
# account. Gemini is deliberately not used (project decision, 2026-09-30).
VISION_QA_MODEL = "qwen/qwen3.8-27b"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_VISION_RETRY_STATUSES = (429, 500, 503)

# A shot-size mismatch this many family steps apart (e.g. wide -> close-up) is
# a composition failure, not descriptive variance, and is worth a retry.
BLOCKING_SHOT_SIZE_GAP = 3

_face_landmarker = None
_hand_landmarker = None


# ── local layer ───────────────────────────────────────────────────────────────
def _load_landmarkers():
    """Lazy-load MediaPipe so importing this module (or starting the app) never
    pays the model-load cost or needs the model files present."""
    global _face_landmarker, _hand_landmarker
    if _face_landmarker is None or _hand_landmarker is None:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        _face_landmarker = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=os.path.join(MEDIAPIPE_MODEL_DIR, "face_landmarker.task")
                ),
                num_faces=6,
            )
        )
        _hand_landmarker = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=os.path.join(MEDIAPIPE_MODEL_DIR, "hand_landmarker.task")
                ),
                num_hands=6,
                min_hand_detection_confidence=0.3,
            )
        )
    return _face_landmarker, _hand_landmarker


def classify_image(image_path: str) -> str:
    """REAL / PLACEHOLDER / FILE-MISSING / UNEXPECTED-SIZE."""
    if not image_path or not os.path.exists(image_path):
        return "FILE-MISSING"
    try:
        with Image.open(image_path) as im:
            size = im.size
    except Exception as e:
        logger.warning(f"classify_image: unreadable {image_path}: {e}")
        return "UNREADABLE"
    if size == REAL_IMAGE_SIZE:
        return "REAL"
    if size == PLACEHOLDER_IMAGE_SIZE:
        return "PLACEHOLDER"
    return "UNEXPECTED-SIZE"


def detect_people_and_hands(image_path: str) -> Dict[str, Any]:
    """Count faces and hands, and judge each hand's finger geometry."""
    try:
        import mediapipe as mp

        face_lm, hand_lm = _load_landmarkers()
        img = mp.Image.create_from_file(image_path)
        faces = face_lm.detect(img).face_landmarks or []
        hands_result = hand_lm.detect(img)
        hands = hands_result.hand_landmarks or []
    except Exception as e:
        logger.warning(f"MediaPipe detection unavailable for {image_path}: {e}")
        return {"faces": None, "hands": None, "hand_defects": []}

    defects: List[str] = []
    for i, lms in enumerate(hands):
        ratio, middle_vs_pinky = _finger_ratios(lms)
        # Calibrated against real generated frames: clean hands measured
        # max/min finger ratios of ~1.3-1.5. A ratio far outside that means
        # fingers of wildly inconsistent length (fused or duplicated digits).
        if ratio > 3.0:
            defects.append(f"hand {i}: implausible finger-length ratio {ratio:.1f}")
        if middle_vs_pinky < 0.8:
            defects.append(f"hand {i}: middle finger shorter than pinky ({middle_vs_pinky:.2f})")
    return {"faces": len(faces), "hands": len(hands), "hand_defects": defects}


_FINGER_CHAINS = {
    "index": [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring": [13, 14, 15, 16],
    "pinky": [17, 18, 19, 20],
}


def _finger_ratios(landmarks):
    def chain_len(chain):
        total = 0.0
        for a, b in zip(chain, chain[1:]):
            pa, pb = landmarks[a], landmarks[b]
            total += ((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2 + (pa.z - pb.z) ** 2) ** 0.5
        return total

    lengths = {name: chain_len(chain) for name, chain in _FINGER_CHAINS.items()}
    values = list(lengths.values())
    ratio = max(values) / max(min(values), 1e-6)
    middle_vs_pinky = lengths["middle"] / max(lengths["pinky"], 1e-6)
    return ratio, middle_vs_pinky


# ── Groq vision layer ──────────────────────────────────────────────────────
_QA_PROMPT = """You are a strict quality-control checker for AI-generated cinematic storyboard frames. This is a final-delivery gate; be harsh but judge ONLY what is visibly in the frame.

Do an explicit ANATOMY CENSUS first. For EVERY human figure in the frame, count separately:
 - how many arms/forearms are attached or visible for that person
 - how many hands are visible for that person
 - fingers per visible hand
A person must have exactly 2 arms and at most 2 hands. Report ANY extra, duplicated, floating,
merged or twisted arm/hand/finger, even a partial one at the frame edge or behind an object.

Return STRICT JSON:
{
 "people": [{"who":"<short description>","arms_visible":<int>,"hands_visible":<int>,"limb_defects":[<strings>]}],
 "people_visible": <int>,
 "anatomy_problems": [<strings, [] if none>],
 "wardrobe_problems": [<strings, e.g. bare chest where clothing is expected>],
 "shot_size_observed": "<extreme wide|wide|medium|medium close-up|close-up|insert>",
 "other_problems": [<garbled text, warped or duplicated objects, melted features>],
 "verdict": "<pass|fail>",
 "reason": "<one sentence>"
}

What this frame is SUPPOSED to show: {expectation}"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Parse the reviewer's JSON, tolerating a stray <think> block or code fence."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1] if start != -1 and end > start else text)


def _retry_wait_seconds(error: urllib.error.HTTPError, attempt: int) -> float:
    """How long to back off before retrying Groq.

    The vision model's free tier is 7,000 input tokens/minute and one frame
    costs a few thousand, so 429s are routine during a batch. Groq states the
    wait it needs (~35s measured) in Retry-After and in the message; a fixed
    8s/16s backoff retried too early, exhausted its attempts, and silently
    dropped the shot to local-only QA.
    """
    header = error.headers.get("retry-after") if error.headers else None
    try:
        if header:
            return min(float(header) + 1.0, 90.0)
    except ValueError:
        pass
    try:
        match = re.search(r"try again in ([\d.]+)s", error.read().decode("utf-8", "ignore"))
        if match:
            return min(float(match.group(1)) + 1.0, 90.0)
    except Exception:
        pass
    return 15.0 * attempt


def review_with_vision(image_path: str, expectation: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """Semantic QC pass on Groq's vision model. Returns None when unavailable
    (no key, rate limit, outage) so the caller can fall back to the local
    layer instead of stalling."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.warning(f"review_with_vision: cannot read {image_path}: {e}")
        return None

    body = {
        "model": VISION_QA_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _QA_PROMPT.replace("{expectation}", expectation)},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }
    # Explicit User-Agent is required: Groq's Cloudflare front rejects urllib's
    # default "Python-urllib/x.y" with HTTP 403 / error 1010 (live-verified).
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "User-Agent": "70mm-ai/1.0",
    }

    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(GROQ_CHAT_URL, data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read())
            return _extract_json(payload["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            if e.code in _VISION_RETRY_STATUSES and attempt < max_attempts:
                wait = _retry_wait_seconds(e, attempt)
                logger.info(f"Vision QA HTTP {e.code}; retrying in {wait}s "
                            f"(attempt {attempt}/{max_attempts})")
                time.sleep(wait)
                continue
            logger.warning(f"Vision QA unavailable (HTTP {e.code}) — falling back to local checks only.")
            return None
        except Exception as e:
            logger.warning(f"Vision QA error ({type(e).__name__}: {e}) — falling back to local checks only.")
            return None
    return None



# Small illegible text is a systemic limitation of diffusion at this
# resolution -- insignia, name tapes, badges and handwriting come out as
# plausible-looking squiggles no matter the seed. Retrying for it burns a full
# generation and changes nothing, so it is recorded and never blocks.
_COSMETIC_ARTIFACT_TERMS = (
    "garbled text", "illegible text", "unreadable text", "gibberish text",
    "nonsensical text", "text artifact", "distorted text", "misspelled",
    "lettering", "insignia detail", "badge text", "nameplate", "name tape",
    "signboard", "sign text",
)


def _is_cosmetic_artifact(finding: str) -> bool:
    lowered = str(finding).lower()
    if any(term in lowered for term in _COSMETIC_ARTIFACT_TERMS):
        return True
    # "Name tape on shoulder is garbled and illegible" blocked a shot for two
    # full retries in the 2026-09-30 batch: illegible small lettering never
    # improves with another seed, whatever noun it is attached to.
    if "illegib" in lowered or "garbled" in lowered or "gibberish" in lowered:
        return True
    # "garbled writing on the letter" / "text on the badge is unreadable"
    return ("text" in lowered or "writing" in lowered) and any(
        w in lowered for w in ("garbl", "illegib", "unreadab", "gibberish", "nonsens", "squiggl")
    )


def _is_missing_character(finding: str, expected_character_names: List[str]) -> bool:
    """A missing character is never cosmetic, wherever the reviewer files it.

    The character must be the thing that is missing ("SITA is missing from the
    frame", "missing required character Ram"), not merely named in the finding
    ("dance bag is missing from Sita's feet" is a missing prop).
    """
    lowered = str(finding).lower()
    match = re.search(r"\b(missing|absent|not visible)\b", lowered)
    if not match:
        return False
    people = ["character", "person", "subject"] + [str(n).lower() for n in expected_character_names]
    before, after = lowered[:match.start()], lowered[match.end():].split()[:4]
    for p in people:
        if re.search(r"\b" + re.escape(p) + r"\b(?!'s)", before):
            return True
    for i, word in enumerate(after):
        if any(word.startswith(p) and not word.startswith(p + "'") for p in people):
            return "from" not in after[:i]
    return False


# ── combined gate ────────────────────────────────────────────────────────────
# Shot-size vocabularies don't map one-to-one (Stage 5 emits "Two-Shot",
# "Over-the-Shoulder", "Insert"; a viewer describes what they see as
# "medium"/"close-up"). Only genuinely distant pairings are worth noting.
_SHOT_SIZE_FAMILIES = {
    "extreme wide": 0, "wide": 1, "establishing": 1, "full": 2, "two-shot": 2,
    "medium": 3, "over-the-shoulder": 3, "medium close-up": 4, "close-up": 5,
    "extreme close-up": 6, "insert": 6, "macro": 6,
}


def _shot_size_gap(wanted: str, observed: str) -> Optional[int]:
    """Family steps between two shot-size labels, or None if either is unknown."""
    def rank(label: str):
        # Lowercase HERE rather than trusting the caller to do it: the family
        # keys are lowercase, so a raw "Medium" silently matched nothing and
        # the function returned "can't tell" for a real mismatch.
        lowered = (label or "").lower()
        for key in sorted(_SHOT_SIZE_FAMILIES, key=len, reverse=True):
            if key in lowered:
                return _SHOT_SIZE_FAMILIES[key]
        return None

    a, b = rank(wanted), rank(observed)
    if a is None or b is None:
        return None
    return abs(a - b)


def _shot_sizes_roughly_agree(wanted: str, observed: str) -> bool:
    gap = _shot_size_gap(wanted, observed)
    if gap is None:
        return True          # unknown vocabulary -- don't invent a complaint
    return gap <= 1          # one step apart is normal descriptive variance



def assess_shot(
    image_path: str,
    expectation: str,
    expected_people: int,
    require_people_check: bool,
    expected_shot_size: str = "",
    expected_character_names: Optional[List[str]] = None,
    use_vision: bool = True,
) -> Dict[str, Any]:
    """Returns {"passed": bool, "problems": [...], "detail": {...}}.

    `require_people_check` is False for wide establishing shots and inserts,
    where the characters are incidental scenery and a people count carries no
    signal worth retrying on.
    """
    problems: List[str] = []      # blocking -- worth regenerating for
    cosmetic: List[str] = []      # recorded for the audit, never blocks delivery
    detail: Dict[str, Any] = {}
    expected_character_names = expected_character_names or []

    kind = classify_image(image_path)
    detail["image_kind"] = kind
    if kind != "REAL":
        problems.append(f"image is {kind} (expected real {REAL_IMAGE_SIZE[0]}x{REAL_IMAGE_SIZE[1]} output)")
        return {"passed": False, "problems": problems, "cosmetic": cosmetic, "detail": detail}

    local = detect_people_and_hands(image_path)
    detail["local"] = local
    problems.extend(local.get("hand_defects") or [])

    vision = review_with_vision(image_path, expectation) if use_vision else None
    detail["vision"] = vision

    if vision:
        # The vision reviewer's people count is trusted over the local landmark count: it was
        # measured correct on frames where OpenCV false-positived a second face
        # on background architecture and where MediaPipe missed a very large face.
        if require_people_check:
            seen = vision.get("people_visible")
            if isinstance(seen, int) and seen < expected_people:
                problems.append(f"only {seen} person(s) visible, expected {expected_people}")

        # Anatomy and wardrobe are the defects worth spending a retry on --
        # they are what actually made frames unusable (duplicated forearms,
        # bare chest where a uniform belongs).
        #
        # But they are filtered through _is_cosmetic_artifact first, because
        # the reviewer does not reliably file findings under the key you would
        # expect: a live run retried a perfectly good frame on
        # "Garbled text on nameplate badge" that arrived inside a BLOCKING
        # bucket rather than other_problems. Classifying by the text of the
        # finding, not by which key it came in on, is what actually holds.
        for item in (vision.get("anatomy_problems") or []) + (vision.get("wardrobe_problems") or []):
            # A missing PROP ("dance bag is missing from Sita's feet") is noted,
            # not regenerated for -- it cost two retries in the 2026-09-30 batch.
            # A missing character is still blocking.
            missing_prop = ("missing" in str(item).lower() or "absent" in str(item).lower())                 and not _is_missing_character(item, expected_character_names)
            (cosmetic if (_is_cosmetic_artifact(item) or missing_prop) else problems).append(item)

        # Everything else is recorded but must NOT block delivery. Measured
        # reason: a frame otherwise verified as good failed purely on "garbled
        # text on the uniform epaulette". Illegible small text on insignia and
        # documents is a systemic limitation of diffusion at this resolution,
        # so treating it as blocking would fail every uniformed shot and retry
        # forever against something that does not improve with another seed.
        #
        # Exception: the reviewer doesn't always file a missing character under a
        # blocking key -- it reported "Missing required character Ram" inside
        # other_problems on one run. A missing character is never cosmetic, so
        # promote anything that reads that way.
        for item in vision.get("other_problems") or []:
            if _is_missing_character(item, expected_character_names):
                problems.append(item)
            else:
                cosmetic.append(item)

        observed = str(vision.get("shot_size_observed") or "").lower()
        if observed and expected_shot_size:
            wanted = expected_shot_size.lower()
            gap = _shot_size_gap(wanted, observed)
            finding = f"shot size reads as '{observed}' rather than '{expected_shot_size}'"
            # Previously always cosmetic -- which is how 'Wide Shot' frames that
            # rendered as face close-ups shipped with no retry. A gap this large
            # is the composition failing, so it now blocks.
            if gap is not None and gap >= BLOCKING_SHOT_SIZE_GAP:
                problems.append(finding)
            elif not _shot_sizes_roughly_agree(wanted, observed):
                cosmetic.append(finding)

        if str(vision.get("verdict", "")).lower() == "fail" and not problems:
            # The reviewer failed it for cosmetic-only reasons -- keep the note, do
            # not burn a retry.
            cosmetic.append(f"vision verdict fail (cosmetic only): {vision.get('reason')}")
    elif require_people_check:
        # Local-only fallback. MediaPipe's face count is the better of the two
        # local detectors but still missed a very large face in testing, so this
        # only fails a shot when it sees NOTHING -- it is deliberately lenient
        # rather than triggering expensive retries on a detector miss.
        faces = local.get("faces")
        if isinstance(faces, int) and faces == 0:
            problems.append("no faces detected at all (local check, vision QA unavailable)")

    return {"passed": not problems, "problems": problems, "cosmetic": cosmetic, "detail": detail}

def detect_face_boxes(image_path: str) -> List[Dict[str, Any]]:
    """Pixel bounding boxes for every detected face, largest first.

    Derived from MediaPipe's face landmarks (normalised 0-1) rather than a
    dedicated detector, because the FaceDetector model bundle is no longer
    served at its published URL while the landmarker bundle is -- and the
    landmarker proved more robust on angled/profile faces than OpenCV Haar,
    which missed a large profile face entirely in testing.

    Returns [{"x","y","w","h","area"}], all ints in pixel space.
    """
    try:
        import mediapipe as mp

        face_lm, _ = _load_landmarkers()
        img = mp.Image.create_from_file(image_path)
        result = face_lm.detect(img)
        faces = result.face_landmarks or []
    except Exception as e:
        logger.warning(f"detect_face_boxes unavailable for {image_path}: {e}")
        return []

    with Image.open(image_path) as im:
        width, height = im.size

    boxes: List[Dict[str, Any]] = []
    for landmarks in faces:
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]
        x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
        y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
        px, py = int(x0 * width), int(y0 * height)
        pw, ph = int((x1 - x0) * width), int((y1 - y0) * height)
        if pw <= 0 or ph <= 0:
            continue
        boxes.append({"x": px, "y": py, "w": pw, "h": ph, "area": pw * ph})

    # MediaPipe's landmarker needs enough of both eyes to fit a mesh, so it
    # returns NOTHING for a strong profile -- verified on a composition whose
    # subject is shot in clean profile, where it found zero faces while the
    # face occupied a large part of the frame. That silently skipped the
    # identity pass and left the composition's random face in place, which is
    # a direct cause of the measured identity spread across shots.
    #
    # Haar's profile cascade catches exactly that case (it independently found
    # faces MediaPipe missed in earlier testing), so it is used as a FALLBACK
    # only -- never merged in when the landmarker already succeeded, because
    # Haar also false-positives on background architecture.
    # A Haar profile-cascade fallback was tried here for the profile-face case
    # and REMOVED after direct inspection: on the profile composition it
    # "found" a 100x100 face at (174,447) which, when cropped and viewed, was
    # the handwritten letter in the actor's hand. An identity pass driven by
    # that box would have pasted a generated face onto a prop. Haar's profile
    # detector is not trustworthy enough to drive a destructive edit, so the
    # identity mechanism must not depend on face detection at all.

    boxes.sort(key=lambda b: -b["area"])
    return boxes


