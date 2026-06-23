import json
import logging
import httpx
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

async def call_openai(prompt: str) -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI key not configured")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def call_gemini(prompt: str, response_schema: Any = None) -> str:
    if not settings.GEMINI_API_KEY:
        raise ValueError("Gemini key not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    if response_schema:
        payload["generationConfig"]["responseSchema"] = response_schema
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

async def call_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_URL}/api/generate"
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["response"]

async def call_gemini_api(prompt: str, response_schema: Any = None) -> str:
    """
    Multi-provider LLM routing engine: OpenAI GPT-4o -> Gemini 2.5 Flash -> Ollama.
    Retries each provider up to 2 times. If all fail, returns empty string for mock fallback.
    """
    # 1. OpenAI GPT-4o
    if settings.OPENAI_API_KEY:
        for attempt in range(2):
            try:
                logger.info(f"Attempting OpenAI GPT-4o (attempt {attempt + 1})...")
                return await call_openai(prompt)
            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {str(e)}")
                
    # 2. Gemini 2.5 Flash
    if settings.GEMINI_API_KEY:
        for attempt in range(2):
            try:
                logger.info(f"Attempting Gemini 2.5 Flash (attempt {attempt + 1})...")
                return await call_gemini(prompt, response_schema)
            except Exception as e:
                logger.warning(f"Gemini attempt {attempt + 1} failed: {str(e)}")
                
    # 3. Ollama (Local)
    for attempt in range(2):
        try:
            logger.info(f"Attempting Ollama Local (attempt {attempt + 1})...")
            return await call_ollama(prompt)
        except Exception as e:
            logger.warning(f"Ollama attempt {attempt + 1} failed: {str(e)}")
            
    logger.error("All configured LLM providers failed. Triggering local mock fallback.")
    return ""

async def generate_story_from_idea(idea: str) -> Dict[str, Any]:
    """
    Task 4: Story Engine
    Generates premise, synopsis, beat sheet, characters, conflict, themes, endings, and act structure.
    """
    prompt = f"""
    Act as a professional creative producer and screenwriter.
    Analyze the following film/story idea: "{idea}"
    
    Generate a full story outline. You must return a JSON object with the following fields:
    - premise: A concise logline/premise.
    - synopsis: A detailed 2-3 paragraph story summary.
    - themes: A list of core themes (strings) explored in the story.
    - conflicts: A dictionary with keys "external" and "internal" detailing the core conflicts.
    - endings: A dictionary with keys "commercial" (a commercial blockbuster ending) and "art_house" (an artistic/ambiguous festival-style ending).
    - beat_sheet: A list of objects. Each object must have "beat_number" (int), "title" (str), and "description" (str). Generate at least 5 key beats.
    - characters: A list of objects. Each object must have "name" (str), "description" (str), "traits" (list of strings), "age" (int), "personality" (str), "weakness" (str), "motivation" (str), "fear" (str), "backstory" (str), and "character_arc" (str).
    - act_structure: A dictionary with keys "act_1" (act structure details and boundaries), "act_2" (development and midpoint twist setup), "act_3" (resolution and climax), and "midpoint_twist" (the structural pivot that occurs exactly halfway).
    
    Format: Return ONLY the raw JSON string. Do not include markdown codeblocks (no ```json).
    """
    
    response_text = ""
    try:
        response_text = await call_gemini_api(prompt)
    except Exception:
        pass
        
    if not response_text:
        # Fallback Mock Data matching the new schema
        return {
            "premise": f"In a world shaped by the idea: '{idea}', a hero confronts their destiny.",
            "synopsis": f"This is a cinematic journey exploring '{idea}'. Following a dramatic incident, our main protagonist is forced to leave their comfort zone. Along with allies, they navigate high-stakes situations that test their limits, eventually leading to a dramatic resolution that changes their world forever.",
            "themes": ["Fate vs. Free Will", "Technological hubris", "Identity and memory"],
            "conflicts": {
                "external": "A race against a decaying system to secure the remaining resources.",
                "internal": "The protagonist's struggle with guilt over a past choice."
            },
            "endings": {
                "commercial": "A high-octane rescue where the protagonist saves the city and reconciles with their family under a sunset.",
                "art_house": "A silent, slow-pan shot of the protagonist looking out at a rain-swept harbor, leaving their final decision ambiguous."
            },
            "beat_sheet": [
                {"beat_number": 1, "title": "The Status Quo", "description": "Introduce the protagonist and the world centered around the premise."},
                {"beat_number": 2, "title": "Inciting Incident", "description": "An unexpected event disrupts their life, presenting a direct challenge related to the idea."},
                {"beat_number": 3, "title": "Rising Action", "description": "The protagonist faces escalating complications and builds a team or finds tools."},
                {"beat_number": 4, "title": "The Climax", "description": "A high-stakes showdown where the protagonist must risk everything."},
                {"beat_number": 5, "title": "Resolution", "description": "The dust settles, showing the new normal and how the world has evolved."}
            ],
            "characters": [
                {
                    "name": "Alex",
                    "description": "The driven leader facing the core challenge.",
                    "traits": ["Determined", "Resilient", "Resourceful"],
                    "age": 32,
                    "personality": "Introspective, quiet, intensely focused.",
                    "weakness": "Inability to trust others, leading to isolation.",
                    "motivation": "To clear their name and protect their younger sibling.",
                    "fear": "Being trapped in the shadows of past failures.",
                    "backstory": "Formerly a chief engineer before a major failure disgraced them.",
                    "character_arc": "Learns to rely on companions, shifting from a solitary survivor to a trusted team leader."
                },
                {
                    "name": "Morgan",
                    "description": "A close companion who challenges the protagonist's views.",
                    "traits": ["Skeptical", "Loyal", "Witty"],
                    "age": 28,
                    "personality": "Extroverted, realistic, quick-witted.",
                    "weakness": "Impulsive and prone to reckless actions.",
                    "motivation": "To uncover the corporate secret that destroyed their family.",
                    "fear": "Irrelevance and being forgotten.",
                    "backstory": "An investigative hacktivist who has lived off the grid for five years.",
                    "character_arc": "Accepts that some truths require patience rather than explosive action."
                }
            ],
            "act_structure": {
                "act_1": "Act I Setup: Establish the world of the protagonist, introduce the inciting incident by Minute 15, and cross the threshold into the special world by Minute 30.",
                "act_2": "Act II Confrontation: Complications rise. Morgan and Alex uncover the depth of the challenge. Action leads up to the midpoint pivot.",
                "act_3": "Act III Climax & Resolution: High stakes race to secure the terminal, followed by a dramatic climax and a slow resolution showing the new normal.",
                "midpoint_twist": "At the exact midpoint, a key ally is revealed to be working for the opposing faction, resetting all stakes."
            }
        }

        
    try:
        # Clean response if markdown blocks were somehow included
        clean_json = re_clean_json(response_text)
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Gemini Story response: {response_text}. Error: {str(e)}")
        # Fallback on parser error
        return {"error": "Failed to parse AI response", "raw": response_text}

async def formulate_scene_ideas(action_line: str) -> Dict[str, Any]:
    """
    Task 5: Scene Formulation Engine
    Generates alternative scene ideas, visual metaphors, conflict suggestions,
    character actions, and emotional subtext.
    """
    prompt = f"""
    Act as a Senior Screenplay Editor.
    Analyze this action line or scene concept: "{action_line}"
    
    Provide creative enhancements. Return a JSON object with the following fields:
    - alternative_ideas: A list of 3 alternative ways this scene could play out.
    - visual_metaphors: A list of 3 visual metaphors to symbolize the mood.
    - conflict_suggestions: A list of 3 ways to introduce or escalate tension here.
    - character_actions: A list of 3 subtle physical actions characters can perform to show emotion.
    - emotional_subtext: A short explanation of the underlying psychological undercurrent.
    
    Format: Return ONLY the raw JSON string. Do not include markdown codeblocks.
    """
    
    response_text = ""
    try:
        response_text = await call_gemini_api(prompt)
    except Exception:
        pass
        
    if not response_text:
        return {
            "alternative_ideas": [
                f"Instead of {action_line}, the scene starts in silence, revealing the action late.",
                f"The action is interrupted by a external phone call or weather event.",
                f"The scene plays out entirely from the perspective of an onlooker."
            ],
            "visual_metaphors": [
                "A flickering bulb overhead, mimicking heartbeat rhythm.",
                "A half-empty glass slowly vibrating on the table edge.",
                "Thick dust motes floating listlessly in a single beam of light."
            ],
            "conflict_suggestions": [
                "A third character enters or is overheard nearby.",
                "The protagonist misplaces a key object needed in this moment.",
                "An unsaid secret hangs heavily, preventing direct conversation."
            ],
            "character_actions": [
                "Constantly wiping clean glasses that are already spotless.",
                "Tear a paper napkin into neat, tiny squares.",
                "Avoid eye contact by focusing intently on a dripping faucet."
            ],
            "emotional_subtext": "Fear of confrontation drives the characters to focus on trivial physical tasks rather than addressing the core issue."
        }
        
    try:
        clean_json = re_clean_json(response_text)
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Gemini Scene Formulation: {response_text}. Error: {str(e)}")
        return {"error": "Failed to parse AI response", "raw": response_text}

async def generate_directors_muse(action_line: str, director_style: str = "Standard") -> Dict[str, Any]:
    """
    Task 6: Director's Muse
    Generates three cinematic shot alternatives based on style (Standard, Kubrick, Fincher, Tarantino, Scorsese, etc.).
    """
    prompt = f"""
    Act as an elite Cinematographer and Director, styling this setup in the distinct cinematic style of: "{director_style}".
    Analyze this action line: "{action_line}"
    
    Generate exactly three distinct cinematic shot alternatives.
    Return a JSON object containing a single list named "alternatives".
    Each item in the list must be a shot recommendation with these fields:
    - shot_size: e.g. Close Up (CU), Extreme Close Up (ECU), Medium Shot (MS), Wide Shot (WS)
    - angle: e.g. Low Angle, High Angle, Eye Level, Dutch Angle
    - movement: e.g. Tracking, Steadicam, Slow Dolly In, Pan, Static
    - lens: e.g. 35mm wide, 85mm anamorphic, 50mm prime
    - lighting: e.g. Low-key chiaroscuro, Harsh overhead fluorescent, Warm golden-hour rim lighting
    - emotion: The core feeling conveyed by this shot setup
    - color_palette: The color scheme (e.g., Cold blue & steel grey, Muted green & amber)
    - visual_tip: A professional tip for composition/framing aligned with the style of {director_style}.
    
    Format: Return ONLY the raw JSON string. Do not include markdown codeblocks.
    """
    
    response_text = ""
    try:
        response_text = await call_gemini_api(prompt)
    except Exception:
        pass
        
    if not response_text:
        return {
            "alternatives": [
                {
                    "shot_size": "Close Up (CU)",
                    "angle": "Low Angle",
                    "movement": "Slow Dolly In",
                    "lens": "85mm anamorphic",
                    "lighting": "Low-key chiaroscuro, sharp side light",
                    "emotion": f"Intense focus in {director_style} style",
                    "color_palette": "Cold steel blue and dark grey shadows",
                    "visual_tip": f"Align composition to match {director_style}'s visual grammar."
                },
                {
                    "shot_size": "Wide Shot (WS)",
                    "angle": "High Angle",
                    "movement": "Static",
                    "lens": "24mm wide-angle",
                    "lighting": "Harsh overhead fluorescent grid, cold and flat",
                    "emotion": f"Vulnerability and isolation in {director_style} style",
                    "color_palette": "Sterile white, cold green tint",
                    "visual_tip": "Center the character in the frame, highlighting the symmetry."
                },
                {
                    "shot_size": "Medium Shot (MS)",
                    "angle": "Eye Level",
                    "movement": "Handheld jittery",
                    "lens": "50mm prime",
                    "lighting": "Warm backlight, dark silhouette foreground",
                    "emotion": f"Panic and urgency in {director_style} style",
                    "color_palette": "Saturated amber and deep black shadows",
                    "visual_tip": "Use a shallow depth of field to draw focus to the character's facial expression."
                }
            ]
        }
        
    try:
        clean_json = re_clean_json(response_text)
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Director's Muse: {response_text}. Error: {str(e)}")
        return {"error": "Failed to parse AI response", "raw": response_text}


async def build_image_prompt(shot_size: str, lens: str, emotion: str, lighting: str, movement: str, action: str) -> Dict[str, Any]:
    """
    Task 11: Prompt Builder
    Converts shot metadata into cinematic positive and negative image prompts.
    """
    prompt = f"""
    Act as a professional prompt engineer for AI image generators (Flux/Stable Diffusion).
    Convert the following film shot metadata into highly detailed, realistic, cinematic prompts:
    - Shot Size: {shot_size}
    - Lens: {lens}
    - Emotion: {emotion}
    - Lighting: {lighting}
    - Movement: {movement}
    - Action: {action}
    
    You must return a JSON object with:
    - positive_prompt: A descriptive prompt focusing on cinematic qualities, framing, camera shot type, lighting detail, film grain, photorealism, color styling.
    - negative_prompt: A list of unwanted elements like bad anatomy, illustrations, low quality, 3D render, cartoon, digital art.
    
    Format: Return ONLY the raw JSON string. Do not include markdown codeblocks.
    """
    
    response_text = ""
    try:
        response_text = await call_gemini_api(prompt)
    except Exception:
        pass
        
    if not response_text:
        return {
            "positive_prompt": f"Cinematic film still, {shot_size}, shot on {lens} lens. {action}. Emotion: {emotion}. Lighting: {lighting}, {movement} camera feeling. 8k resolution, highly detailed, photorealistic, film grain, dramatic shadows, color graded, masterpiece.",
            "negative_prompt": "3d render, cartoon, illustration, drawing, painting, bad anatomy, deformed face, extra limbs, low quality, ugly, watermark, text"
        }
        
    try:
        clean_json = re_clean_json(response_text)
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Prompt Builder: {response_text}. Error: {str(e)}")
        return {"error": "Failed to parse AI response", "raw": response_text}

def re_clean_json(text: str) -> str:
    """Helper to strip markdown tags or extra spaces from JSON string."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

async def validate_scene_continuity(scene_data: Dict[str, Any], shots_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Task 11: Continuity Engine
    Validates characters, props, locations, wardrobe, and time continuity between scene content and shot designs.
    """
    prompt = f"""
    Act as an expert script supervisor and continuity coordinator.
    Analyze the screenplay scene content and its corresponding shot list for continuity errors.
    
    Scene Data:
    {json.dumps(scene_data, indent=2)}
    
    Shot List:
    {json.dumps(shots_data, indent=2)}
    
    Identify potential continuity issues, including:
    1. Characters mentioned in action or dialogue but not referenced in shot notes or properties.
    2. Props/wardrobe mentioned in action lines but missing or inconsistent in shot descriptions.
    3. Lighting, day/night setting, or time mismatch (e.g. scene heading is 'NIGHT' but shots are marked as 'Day').
    4. Location discrepancies.
    
    Return a JSON array of objects, each containing:
    - "type": one of "character", "prop", "location", "wardrobe", "time", "general"
    - "severity": "warning" or "error"
    - "description": clear explanation of the continuity issue
    - "fix_suggestion": actionable recommendation on how to resolve it
    - "auto_fixable": boolean value (true if it can be applied directly to database fields)
    - "fix_data": dictionary of updates to apply (e.g. {{"shot_id": "xyz", "updates": {{"day_night": "Night"}}}} or {{"shot_id": "xyz", "updates": {{"notes": "Add props..."}}}})
    
    Format response strictly as a JSON array.
    """
    
    response_text = ""
    try:
        response_text = await call_gemini_api(prompt)
    except Exception:
        pass
        
    if not response_text:
        # Fallback heuristic rules checking
        warnings = []
        # Check day_night vs heading
        scene_heading = (scene_data.get("heading") or "").upper()
        is_night_scene = "NIGHT" in scene_heading
        
        for idx, shot in enumerate(shots_data):
            shot_dn = (shot.get("day_night") or "Day").upper()
            if is_night_scene and "DAY" in shot_dn:
                warnings.append({
                    "type": "time",
                    "severity": "warning",
                    "description": f"Shot {shot.get('shot_number')} day_night is '{shot.get('day_night')}' but scene heading indicates NIGHT.",
                    "fix_suggestion": "Set day_night property of the shot to 'Night'.",
                    "auto_fixable": True,
                    "fix_data": {"shot_id": shot.get("id"), "updates": {"day_night": "Night"}}
                })
            
            # Check characters mentioned in dialogues but absent in notes
            for dialogue in scene_data.get("dialogues", []):
                char_name = dialogue.get("character_name", "").lower()
                notes = (shot.get("notes") or "").lower()
                visual_tip = (shot.get("visual_tip") or "").lower()
                if char_name not in notes and char_name not in visual_tip:
                    warnings.append({
                        "type": "character",
                        "severity": "warning",
                        "description": f"Dialogue of {dialogue.get('character_name')} present in scene, but shot {shot.get('shot_number')} notes do not reference this character.",
                        "fix_suggestion": f"Ensure {dialogue.get('character_name')} is framed in the shot or add visual description.",
                        "auto_fixable": True,
                        "fix_data": {"shot_id": shot.get("id"), "updates": {"notes": f"{dialogue.get('character_name')} reacts. " + (shot.get("notes") or "")}}
                    })
        return warnings
        
    try:
        clean_json = re_clean_json(response_text)
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Continuity checker response: {response_text}. Error: {str(e)}")
        return [{"type": "general", "severity": "warning", "description": "AI analysis returned unparseable content.", "fix_suggestion": "Check shot list values manually.", "auto_fixable": False, "fix_data": {}}]
