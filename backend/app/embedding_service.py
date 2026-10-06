"""
Shared visual embedding service — self-hosted, free, MIT-licensed (OpenAI's
original CLIP weights via open_clip). Deliberately a general-purpose visual
embedding, NOT a face-recognition-specific model: the spec explicitly flags
InsightFace/IP-Adapter-FaceID/InstantID as license risks for a commercial
code path, so both Stage 6 (character identity embedding, stored on
Character.embedding_vector) and Stage 9 (continuity QA similarity checks)
reuse this same model instead of a dedicated face model.

The model is lazy-loaded on first use (not at import time) so importing this
module — or starting the app — never pays the load cost or requires network
access unless a character/continuity endpoint actually needs an embedding.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_MODEL_NAME = "ViT-B-32-quickgelu"  # the "-quickgelu" variant is required to exactly match OpenAI's original CLIP architecture; plain "ViT-B-32" silently mismatches (quick_gelu=False vs the checkpoint's True)
_PRETRAINED = "openai"  # MIT-licensed original CLIP weights, not a LAION checkpoint

_model = None
_preprocess = None
_load_error: Optional[str] = None


def _load_model() -> bool:
    """Returns True if the model is ready to use. Caches failure too, so a
    missing dependency/no network doesn't retry a slow failing import on
    every single call."""
    global _model, _preprocess, _load_error
    if _model is not None:
        return True
    if _load_error is not None:
        return False
    try:
        import open_clip  # heavy import — kept local to this function on purpose
        model, _, preprocess = open_clip.create_model_and_transforms(_MODEL_NAME, pretrained=_PRETRAINED)
        model.eval()
        _model = model
        _preprocess = preprocess
        return True
    except Exception as e:
        _load_error = str(e)
        logger.error(f"Failed to load CLIP model ({_MODEL_NAME}/{_PRETRAINED}): {e}")
        return False


def is_available() -> bool:
    return _load_model()


def compute_image_embedding(image_path: str) -> Optional[List[float]]:
    """Returns an L2-normalized CLIP image embedding as a plain float list
    (JSON-serializable, ready for Character.embedding_vector / continuity
    comparisons), or None if the model/image can't be loaded."""
    if not _load_model():
        return None
    try:
        import torch
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        tensor = _preprocess(image).unsqueeze(0)
        with torch.no_grad():
            features = _model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze(0).tolist()
    except Exception as e:
        logger.error(f"Failed to compute embedding for '{image_path}': {e}")
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Plain-Python cosine similarity — no numpy dependency needed for a
    single pair comparison, and it keeps this function usable/testable even
    when torch/open_clip aren't installed."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
