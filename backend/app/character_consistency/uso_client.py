"""
USO param builder — ByteDance's USO ([CVPR 2026], Apache 2.0, no InsightFace
or other non-commercial-restricted dependency; verified directly against
github.com/bytedance/USO) unifies style- and subject-driven generation on
top of Flux.1-dev, and is the successor to ByteDance's earlier UNO model.

This build originally used UNO via the jax-explorer/ComfyUI-UNO community
custom node, but live GPU testing (Kaggle T4) found a reproducible bug in
that third-party node's reference-image conditioning path: generation with
ANY reference image (synthetic or a real photo) produced a near-flat,
degenerate output, while UNO's own reference-free text-to-image path was
confirmed healthy. Root-caused down to prepare_multi_ip/denoise in
uno/flux/sampling.py without finding the exact defect — likely something in
how that wrapper's node feeds ref_img/ref_img_ids into the Flux transformer.

Switched to USO instead because it has NATIVE ComfyUI support — built
entirely from standard core nodes (CheckpointLoaderSimple, LoraLoaderModelOnly,
ReferenceLatent, FluxKontextMultiReferenceLatentMethod, FluxGuidance, etc. —
see comfy_workflow_builder.py's USO docstring for the exact graph, reverse-
engineered from ComfyUI's own official workflow template), not a third-party
custom node, which removes this whole class of bug. Same Apache 2.0 license
as UNO, so no licensing regression versus the original PhotoMaker
V2/InsightFace-avoidance reasoning.

Used for every shot with 1+ named characters — USO's reference-conditioning
mechanism (chained ReferenceLatent calls + FluxKontextMultiReferenceLatentMethod
in "uxo/uno" mode) natively handles both single- and multi-subject identity
conditioning the same way UNO did.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class USOClient:
    def build_uso_params(self, characters: List[Dict[str, Any]], strength: float = 0.7) -> Dict[str, Any]:
        """`characters`: list of {"name", "reference_image_paths"} — one
        entry per named character present in the shot (1 or more)."""
        if not characters:
            raise ValueError("USO requires at least one named character with locked reference images.")
        logger.info(f"Building USO params for {len(characters)} identities: {[c.get('name') for c in characters]}")
        return {
            "node_type": "USO",
            "identities": [
                {
                    "name": c.get("name"),
                    "reference_image_paths": (c.get("reference_image_paths") or [])[:4],
                    # The per-face identity pass prompts each face with its own
                    # character's description rather than the whole-shot text.
                    **({"description": c["description"]} if c.get("description") else {}),
                }
                for c in characters
            ],
            "strength": strength,
        }
