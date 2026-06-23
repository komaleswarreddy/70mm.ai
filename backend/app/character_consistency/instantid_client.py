import logging

logger = logging.getLogger(__name__)

class InstantIDClient:
    def __init__(self, endpoint_url: str = "http://localhost:8188"):
        self.endpoint_url = endpoint_url

    def build_instantid_params(self, face_image_url: str, strength: float = 0.8) -> dict:
        """
        Builds the parameters for InstantID controlnet node injection.
        """
        logger.info(f"Building InstantID params for face: {face_image_url} (weight: {strength})")
        return {
            "node_type": "InstantIDFaceAnalysis",
            "image_url": face_image_url,
            "strength": strength,
            "keypoints_lock": True
        }
