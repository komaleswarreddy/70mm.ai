import os
import json
import logging
from PIL import Image, ImageDraw, ImageFilter
from typing import Dict, Any, Optional
from app.comfy_client import ComfyClient

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "storyboards")
os.makedirs(STATIC_DIR, exist_ok=True)

class ImageService:
    def __init__(self):
        self.comfy = ComfyClient()
        self.workflow_path = os.path.join(os.path.dirname(__file__), "workflow.json")
        self.workflow = {}
        if os.path.exists(self.workflow_path):
            try:
                with open(self.workflow_path, "r") as f:
                    self.workflow = json.load(f)
            except Exception as e:
                logger.error(f"Error loading workflow.json: {str(e)}")

    async def generate_storyboard(self, shot_id: str, scene_heading: str, shot_info: Dict[str, Any], prompt: str, negative_prompt: str) -> str:
        """
        Generates storyboard image and returns the file path/url.
        Uses ComfyUI if available, otherwise draws a premium cinematic placeholder image using Pillow.
        """
        filename = f"shot_{shot_id}.png"
        file_path = os.path.join(STATIC_DIR, filename)
        
        # Try ComfyUI first
        if await self.comfy.is_healthy() and self.workflow:
            logger.info("ComfyUI server is healthy. Running generation...")
            img_bytes = await self.comfy.generate_image(self.workflow, prompt, negative_prompt)
            if img_bytes:
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                return f"/static/storyboards/{filename}"
                
        # Fallback: Draw a premium cinematic visual concept using Pillow
        logger.info("ComfyUI not available. Generating premium local visual placeholder using Pillow...")
        
        width, height = 1024, 512
        img = Image.new("RGBA", (width, height), color="#000000")
        draw = ImageDraw.Draw(img)
        
        # Background Gradient
        c1 = (10, 10, 18)   # Deep space dark blue
        c2 = (30, 25, 45)   # Indigo/charcoal
        for y in range(height):
            ratio = y / height
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
            
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ol_draw = ImageDraw.Draw(overlay)
        
        # Determine theme color based on prompt
        light_color = (255, 140, 50, 80)
        p_lower = prompt.lower()
        if "sunset" in p_lower or "warm" in p_lower or "golden" in p_lower:
            light_color = (255, 120, 60, 120)
        elif "cold" in p_lower or "blue" in p_lower or "neon" in p_lower:
            light_color = (0, 180, 255, 100)
        elif "forest" in p_lower or "green" in p_lower:
            light_color = (50, 200, 120, 100)
            
        # Draw visual silhouette circles to simulate composition
        ol_draw.ellipse([width//2 - 200, height//2 - 150, width//2 + 200, height//2 + 150], fill=light_color)
        ol_draw.rectangle([0, height - 120, width, height], fill=(15, 12, 22, 255))
        ol_draw.ellipse([width//3 - 60, height//2 - 40, width//3 + 60, height//2 + 80], fill=(5, 5, 8, 255)) # Subject silhouette
        
        # Apply blur to overlay
        blurred_overlay = overlay.filter(ImageFilter.GaussianBlur(35))
        img = Image.alpha_composite(img, blurred_overlay)
        draw = ImageDraw.Draw(img)
        
        # Cinematic letterbox
        letterbox_h = 40
        draw.rectangle([0, 0, width, letterbox_h], fill=(0, 0, 0, 220))
        draw.rectangle([0, height - letterbox_h, width, height], fill=(0, 0, 0, 220))
        
        # Framing safety guide lines
        draw.rectangle([20, 20, width - 20, height - 20], outline=(100, 100, 150, 30), width=1)
        
        # Header Text
        header_text = f"70MM AI STORYBOARD  |  SCENE: {scene_heading.upper()}"
        draw.text((30, 12), header_text, fill=(200, 200, 255, 200))
        
        # Specs Text
        shot_size = shot_info.get("shot_size", "MS")
        angle = shot_info.get("angle", "Eye Level")
        lens = shot_info.get("lens", "50mm")
        movement = shot_info.get("movement", "Static")
        lighting = shot_info.get("lighting", "Natural")
        emotion = shot_info.get("emotion", "Neutral")
        
        specs_text = f"SHOT: {shot_info.get('shot_number', 1)}  |  {shot_size}  |  {angle}  |  {lens}  |  {movement}  |  {lighting}  |  {emotion.upper()}"
        draw.text((30, height - 28), specs_text, fill=(150, 255, 200, 200))
        
        # Prompt wrap text
        max_chars = 90
        prompt_preview = prompt[:160] + "..." if len(prompt) > 160 else prompt
        prompt_lines = [prompt_preview[i:i+max_chars] for i in range(0, len(prompt_preview), max_chars)]
        
        y_offset = height - 100
        for line in prompt_lines:
            draw.text((50, y_offset), f"PROMPT: {line}", fill=(220, 220, 220, 180))
            y_offset += 16
            
        img.convert("RGB").save(file_path, "PNG")
        return f"/static/storyboards/{filename}"
