import logging
from typing import Dict, Any
from app.character_consistency.instantid_client import InstantIDClient
from app.character_consistency.ipadapter_client import IPAdapterClient

logger = logging.getLogger(__name__)

class CharacterConsistencyOrchestrator:
    def __init__(self):
        self.instantid = InstantIDClient()
        self.ipadapter = IPAdapterClient()

    def compile_consistency_params(
        self,
        reference_image_url: str,
        face_lock: bool = True,
        hair_lock: bool = False,
        costume_lock: bool = False,
        strength: float = 0.7
    ) -> Dict[str, Any]:
        """
        Synthesizes configuration nodes for ComfyUI.
        """
        logger.info(f"Orchestrating consistency check for face reference {reference_image_url}")
        
        configs = {
            "reference_image_url": reference_image_url,
            "overall_strength": strength,
            "locks": {
                "face": face_lock,
                "hair": hair_lock,
                "costume": costume_lock
            }
        }
        
        if face_lock:
            configs["instantid"] = self.instantid.build_instantid_params(reference_image_url, strength)
            
        if hair_lock or costume_lock:
            # IPAdapter handles costume / style weight preservation
            configs["ipadapter"] = self.ipadapter.build_ipadapter_params(reference_image_url, strength * 0.8)
            
        return configs
