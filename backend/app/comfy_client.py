import json
import logging
import uuid
import httpx
import asyncio
import random
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class ComfyClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.COMFYUI_URL
        
    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/object_info")
                return res.status_code == 200
        except Exception:
            return False
            
    async def generate_image(self, workflow_dict: Dict[str, Any], positive_prompt: str, negative_prompt: str) -> Optional[bytes]:
        """
        Sends the workflow to ComfyUI, polls for execution, and returns image bytes.
        """
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
            
        # Randomize KSampler seed
        for node_id, node in workflow.items():
            if node.get("class_type") == "KSampler":
                node["inputs"]["seed"] = random.randint(1, 10**15)
                
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": client_id}
                )
                response.raise_for_status()
                res_json = response.json()
                prompt_id = res_json["prompt_id"]
                
                # Poll history for completion
                for _ in range(60):
                    await asyncio.sleep(2.0)
                    history_response = await client.get(f"{self.base_url}/history/{prompt_id}")
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
                                    img_res = await client.get(img_url)
                                    if img_res.status_code == 200:
                                        return img_res.content
                            break
        except Exception as e:
            logger.error(f"ComfyUI generation error: {str(e)}")
            
        return None
