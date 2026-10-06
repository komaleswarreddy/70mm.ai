"""
Embedding service tests. cosine_similarity is pure Python and tested purely.
The real CLIP model load + inference is exercised once end-to-end against
tiny synthetic images — the model is self-hosted (open_clip, MIT-licensed
OpenAI CLIP weights) and gets cached locally after the first run, so this
isn't a repeated network dependency in practice, matching the "free,
self-hostable" constraint the whole character-consistency system relies on.
"""
import tempfile
import os
import pytest
from PIL import Image

from app.embedding_service import cosine_similarity, compute_image_embedding, is_available


# ── cosine_similarity — pure math, no model needed ──────────────────────────

def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

def test_cosine_similarity_opposite_vectors():
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

def test_cosine_similarity_empty_or_mismatched_returns_zero():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1, 2], [1, 2, 3]) == 0.0

def test_cosine_similarity_zero_vector_returns_zero():
    assert cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0


# ── real CLIP model — one end-to-end check with tiny synthetic images ───────

@pytest.mark.skipif(not is_available(), reason="CLIP model/deps not available in this environment")
def test_compute_image_embedding_real_model_similar_vs_different_images():
    paths = []
    try:
        p1 = tempfile.mktemp(suffix=".png")
        p2 = tempfile.mktemp(suffix=".png")
        p3 = tempfile.mktemp(suffix=".png")
        paths = [p1, p2, p3]
        Image.new("RGB", (64, 64), color=(120, 50, 200)).save(p1)
        Image.new("RGB", (64, 64), color=(122, 52, 198)).save(p2)  # near-identical
        Image.new("RGB", (64, 64), color=(10, 200, 10)).save(p3)   # clearly different

        e1 = compute_image_embedding(p1)
        e2 = compute_image_embedding(p2)
        e3 = compute_image_embedding(p3)

        assert e1 is not None and len(e1) == 512
        sim_similar = cosine_similarity(e1, e2)
        sim_different = cosine_similarity(e1, e3)
        assert sim_similar > sim_different
        assert sim_similar > 0.99  # near-identical solid colors should be almost identical
    finally:
        for p in paths:
            if os.path.exists(p):
                os.remove(p)

def test_compute_image_embedding_missing_file_returns_none():
    assert compute_image_embedding("/nonexistent/path/to/image.png") is None
