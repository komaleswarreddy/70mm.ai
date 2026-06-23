import math
from typing import List

class SentenceEmbeddingEngine:
    """
    Manages vector representations of text.
    Uses lightweight word frequency hash overlapping as fallback if external weights are unavailable.
    """
    def __init__(self):
        pass

    def get_embedding(self, text: str) -> List[float]:
        # Simple word frequency vectorizer fallback
        words = text.lower().split()
        vector = [0.0] * 128
        for w in words:
            # Deterministic hash to map word into 128 dimensional space
            idx = hash(w) % 128
            vector[idx] += 1.0
        
        # Normalize vector
        sq_sum = sum(val**2 for val in vector)
        if sq_sum > 0:
            norm = math.sqrt(sq_sum)
            vector = [val / norm for val in vector]
        return vector

    def compute_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        return sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
