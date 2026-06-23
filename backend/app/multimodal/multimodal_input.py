import logging
from typing import Dict, Any
from app.multimodal.voice_parser import VoiceScriptParser
from app.multimodal.image_scene_analyzer import ImageSceneAnalyzer
from app.multimodal.moodboard_parser import MoodboardParser

logger = logging.getLogger(__name__)

class MultimodalInputEngine:
    def __init__(self):
        self.voice = VoiceScriptParser()
        self.image = ImageSceneAnalyzer()
        self.moodboard = MoodboardParser()

    async def process_multimodal_asset(self, asset_type: str, file_path: str) -> Dict[str, Any]:
        """
        Routes the file to the correct sub-parser based on file type.
        """
        logger.info(f"Processing multimodal asset: {asset_type} ({file_path})")
        
        if asset_type == "voice":
            script = await self.voice.transcribe_audio_to_fountain(file_path)
            return {"type": "voice", "content": script}
            
        elif asset_type == "image_ref":
            analysis = await self.image.analyze_image_ref(file_path)
            return {"type": "image_ref", "analysis": analysis}
            
        elif asset_type == "moodboard":
            palette = await self.moodboard.extract_color_palette(file_path)
            return {"type": "moodboard", "palette": palette}
            
        return {"error": "Unsupported asset type"}
