# Comfy Client Module
import json
import logging
import uuid
import httpx
import asyncio
import random
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Tracks which model "family" (plain Flux vs USO) is currently cached in the
# shared ComfyUI instance's VRAM/RAM, across separate ComfyClient instances
# and requests (module-level, not per-instance, since it describes shared
# server-side state, not anything local to one client object).
#
# Real incident this guards against: live-tested on a Kaggle T4 (31GB system
# RAM) with an earlier UNO-based integration (see comfy_workflow_builder.py's
# module docstring for why USO replaced it), alternating plain-Flux and
# character-conditioned generations on the same long-lived ComfyUI process
# caused BOTH model families' weights to stay cached simultaneously (ComfyUI
# only evicts a cached node output when that node's own inputs change, so a
# different node type/id is never recognized as "the same resource" to
# evict, even though both held a large fp8 copy of essentially the same
# Flux checkpoint — the plain path's UNETLoader-loaded flux1-dev.safetensors
# vs the character path's own checkpoint). That redundant double-residency
# exhausted system RAM (confirmed via `free -h` showing 26/31GB used while
# `nvidia-smi` showed only 225MB/15360MB VRAM used at the moment of death —
# never a GPU problem), first degrading output quality (a diffusion pass
# under severe memory pressure produced near-flat, low-detail images on two
# separate live runs) and eventually getting the ComfyUI process SIGKILLed
# by the Linux OOM-killer with zero traceback. The same risk applies to USO
# (CheckpointLoaderSimple loads its OWN separate all-in-one checkpoint file,
# flux1-dev-fp8.safetensors, distinct from the plain path's flux1-dev.safetensors)
# so this guard stays in place. Calling ComfyUI's own /free endpoint only on
# an actual family switch avoids paying a full reload on every single
# request (the common case of several consecutive shots using the same
# approach stays fast) while still preventing the two families from ever
# being resident together.
_last_workflow_engine: Optional[str] = None


def _workflow_engine(workflow_dict: Dict[str, Any]) -> str:
    for node in workflow_dict.values():
        if node.get("class_type") == "CheckpointLoaderSimple":
            return "USO"
    return "plain"


class ComfyClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.COMFYUI_URL
        
    async def is_healthy(self) -> bool:
        """
        A free Cloudflare quick tunnel (the expected self-hosted setup here)
        has real, observed transient latency spikes/reconnects — a single
        blip past this check's own timeout was enough to skip the entire
        generation straight to the Pillow placeholder with no retry at all,
        even though ComfyUI itself was fine moments before and after. Two
        quick attempts with a more forgiving per-attempt timeout is a better
        match for that failure mode than one strict, fast check.
        """
        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(f"{self.base_url}/object_info")
                    if res.status_code == 200:
                        return True
            except Exception:
                pass
        return False

    async def upload_image(self, image_bytes: bytes, filename: str) -> Optional[str]:
        """
        Pushes reference-image bytes into ComfyUI's own input/ folder via
        its /upload/image endpoint — a LoadImage node can only reference a
        file already sitting there by filename, not an arbitrary path on
        our side (relevant when ComfyUI runs on a separate machine, e.g. a
        Kaggle GPU, which is the expected free/self-hosted setup here).
        Returns the filename to use in a LoadImage node's "image" input
        (echoes back what we sent, but via the server's response so a
        future rename/overwrite policy change doesn't silently desync us).
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/upload/image",
                    files={"image": (filename, image_bytes, "image/png")},
                    data={"overwrite": "true"},
                )
                response.raise_for_status()
                return response.json().get("name", filename)
        except Exception as e:
            logger.error(f"ComfyUI image upload error for '{filename}': {str(e)}")
            return None

    async def free_cached_models(self) -> None:
        """Unloads whatever models ComfyUI currently has cached in VRAM/RAM.
        See the module-level comment on _last_workflow_engine for why this
        matters — call before switching between the plain-Flux and USO
        graphs, not on every request."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(f"{self.base_url}/free", json={"unload_models": True, "free_memory": True})
        except Exception as e:
            logger.warning(f"ComfyUI /free call failed (continuing anyway): {str(e)}")

    async def generate_image(
        self, workflow_dict: Dict[str, Any], positive_prompt: str, negative_prompt: str, seed: Optional[int] = None
    ) -> Optional[bytes]:
        """
        Sends the workflow to ComfyUI, polls for execution, and returns image bytes.
        """
        global _last_workflow_engine
        engine = _workflow_engine(workflow_dict)
        if _last_workflow_engine is not None and _last_workflow_engine != engine:
            logger.info(f"ComfyUI model family switch ({_last_workflow_engine} -> {engine}) — freeing cached models first.")
            await self.free_cached_models()
        _last_workflow_engine = engine

        client_id = str(uuid.uuid4())
        
        # Make a deep copy to avoid mutations
        workflow = json.loads(json.dumps(workflow_dict))
        
        # Detect and set prompt text
        pos_node_id = None
        neg_node_id = None
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            if class_type == "CLIPTextEncode":
                if pos_node_id is None:
                    pos_node_id = node_id
                else:
                    neg_node_id = node_id
                    
        if pos_node_id:
            workflow[pos_node_id]["inputs"]["text"] = positive_prompt
        if neg_node_id:
            workflow[neg_node_id]["inputs"]["text"] = negative_prompt
            
        # Stage 6 needs a REPRODUCIBLE seed for locked character references
        # (spec: "generated once with a fixed seed and then frozen"); every
        # other caller wants a fresh one each time — randomize only when the
        # caller didn't pass one. Both the plain and USO graphs use a
        # standard KSampler (see comfy_workflow_builder.py).
        resolved_seed = seed if seed is not None else random.randint(1, 10**15)
        for node_id, node in workflow.items():
            if node.get("class_type") == "KSampler":
                node["inputs"]["seed"] = resolved_seed

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": client_id}
                )
                response.raise_for_status()
                res_json = response.json()
                prompt_id = res_json["prompt_id"]

                # Poll history for completion — real GPU inference (Flux,
                # even at fp8) can take well over a minute, especially on a
                # cold model load, so this allows up to 10 minutes total.
                #
                # Each iteration's own network call is caught separately —
                # live-tested against a real Cloudflare quick tunnel, which
                # is prone to brief mid-session reconnects (verified via its
                # own QUIC "no recent network activity" errors), one such
                # blip mid-poll used to abort the whole wait and report
                # FAILED even though ComfyUI had genuinely finished the
                # generation server-side (confirmed by pulling the completed
                # result straight from /history afterwards). A transient
                # hiccup on one poll should cost one retry, not the result.
                for _ in range(300):
                    await asyncio.sleep(2.0)
                    try:
                        history_response = await client.get(f"{self.base_url}/history/{prompt_id}")
                    except Exception as poll_err:
                        logger.warning(f"ComfyUI history poll hiccup (retrying): {str(poll_err)}")
                        continue
                    if history_response.status_code == 200:
                        history_json = history_response.json()
                        if prompt_id in history_json:
                            outputs = history_json[prompt_id].get("outputs", {})
                            for node_id, output in outputs.items():
                                if "images" in output:
                                    img_info = output["images"][0]
                                    filename = img_info["filename"]
                                    subfolder = img_info.get("subfolder", "")
                                    folder_type = img_info.get("type", "output")

                                    img_url = f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={folder_type}"
                                    try:
                                        img_res = await client.get(img_url)
                                    except Exception as fetch_err:
                                        logger.error(f"ComfyUI finished generating but the image fetch itself failed: {str(fetch_err)}")
                                        return None
                                    if img_res.status_code == 200:
                                        return img_res.content
                            break
        except Exception as e:
            logger.error(f"ComfyUI generation error: {str(e)}")

        return None

