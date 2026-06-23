import logging

logger = logging.getLogger(__name__)

class IPAdapterClient:
    def __init__(self, endpoint_url: str = "http://localhost:8188"):
        self.endpoint_url = endpoint_url

    def build_ipadapter_params(self, reference_image_url: str, weight: float = 0.6) -> dict:
        """
        Builds parameters for IPAdapter reference conditioning.
        """
        logger.info(f"Building IPAdapter parameters for image: {reference_image_url} (weight: {weight})")
        return {
            "node_type": "IPAdapterUnifiedLoader",
            "reference_image_url": reference_image_url,
            "weight": weight,
            "style_transfer": True,
            "costume_lock": True
        }
