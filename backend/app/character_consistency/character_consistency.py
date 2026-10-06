"""
Stage 6 — character asset & consistency system.

Routes every shot with 1+ named characters through USO (see uso_client.py
for why UNO/PhotoMaker V2 were dropped). Enforces the spec's hard rule:
never generate a character's first appearance without first creating and
locking their reference set.
"""
import logging
from typing import Any, Dict, List

from app.character_consistency.uso_client import USOClient

logger = logging.getLogger(__name__)


class CharacterConsistencyOrchestrator:
    def __init__(self):
        self.uso = USOClient()

    def compile_consistency_params(self, characters: List[Dict[str, Any]], strength: float = 0.7) -> Dict[str, Any]:
        """
        `characters`: list of {"name", "reference_image_paths", "is_locked"}
        — one entry per named character present in a shot.

        Raises ValueError if any listed character isn't locked yet, rather
        than silently generating an unlocked/inconsistent identity — the
        caller (Stage 7's image generation route) should call
        POST /characters/{id}/lock-reference first and surface that error.
        """
        if not characters:
            return {"engine": None, "reason": "No named characters in this shot."}

        unlocked = [c["name"] for c in characters if not c.get("is_locked")]
        if unlocked:
            raise ValueError(
                f"Cannot generate this shot — character(s) not yet locked: {', '.join(unlocked)}. "
                "Call POST /characters/{id}/lock-reference first."
            )

        params = self.uso.build_uso_params(characters, strength)
        return {"engine": "USO", "characters": [c["name"] for c in characters], **params}
