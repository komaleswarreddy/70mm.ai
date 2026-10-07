# AI Service Module
import json
import logging
import re
import httpx
from typing import Dict, Any, List
from app.config import settings
from app.shot_planner import SHOT_TYPES, DEFAULT_CINEMATOGRAPHY, default_cinematography_for_shot_type, suggest_shot_plan

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

# The project's one text model. Gemini is deliberately not used anywhere
# (project decision, 2026-09-30) -- do not add it back as a fallback.
GROQ_TEXT_MODEL = "openai/gpt-oss-120b"

async def call_groq(prompt: str) -> str:
    """
    Primary text provider: Groq, openai/gpt-oss-120b (OpenAI's open-weight
    model, trained with structured-output/JSON reliability as a stated goal,
    which matters for this codebase's schema-constrained generation calls).
    OpenAI-compatible endpoint, so this reuses the same request/response
    shape as call_openai() above.

    Timeout is 60s rather than the 15s used with gpt-oss-20b: 120b spends
    reasoning tokens before answering, and the Stage 4/5 shot-plan prompts
    are long enough that 15s would time out on a healthy request.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("Groq key not configured")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_TEXT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

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

async def call_llm(prompt: str, response_schema: Any = None) -> str:
    """
    Multi-provider LLM routing engine: Groq gpt-oss-120b -> OpenAI GPT-4o -> Ollama.
    Retries each provider up to 2 times. If all fail, returns empty string for mock fallback.

    `response_schema` is accepted for call-site compatibility but not sent:
    every provider here is asked for a JSON object and each caller validates
    the shape itself.
    """
    # 1. Groq (openai/gpt-oss-120b)
    if settings.GROQ_API_KEY:
        for attempt in range(2):
            try:
                logger.info(f"Attempting Groq {GROQ_TEXT_MODEL} (attempt {attempt + 1})...")
                return await call_groq(prompt)
            except Exception as e:
                logger.warning(f"Groq attempt {attempt + 1} failed: {str(e)}")

    # 2. OpenAI GPT-4o
    if settings.OPENAI_API_KEY:
        for attempt in range(2):
            try:
                logger.info(f"Attempting OpenAI GPT-4o (attempt {attempt + 1})...")
                return await call_openai(prompt)
            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {str(e)}")

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
      IMPORTANT for "description": this text is fed directly to an image model to generate every shot this character appears in, so it must be CONCRETE and VISUAL, roughly 30-50 words, and must state:
        (a) exact age and build, skin tone, face shape, hair and facial hair;
        (b) their DEFAULT WARDROBE explicitly (garments, colours, how they are worn) -- never leave clothing unstated, or the image model improvises it and characters come out half-dressed or differently dressed in every shot;
        (c) one or two distinctive physical details (a scar, spectacles, specific jewellery).
      Avoid vague phrases like "authentic features", "handsome", "striking" or "typical" -- they give the image model nothing to anchor on and produce generic, idealised faces.
    - act_structure: A dictionary with keys "act_1" (act structure details and boundaries), "act_2" (development and midpoint twist setup), "act_3" (resolution and climax), and "midpoint_twist" (the structural pivot that occurs exactly halfway).
    
    Format: Return ONLY the raw JSON string. Do not include markdown codeblocks (no ```json).
    """
    
    response_text = ""
    try:
        response_text = await call_llm(prompt)
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
        logger.error(f"Failed to parse LLM Story response: {response_text}. Error: {str(e)}")
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
        response_text = await call_llm(prompt)
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
        logger.error(f"Failed to parse LLM Scene Formulation: {response_text}. Error: {str(e)}")
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
        response_text = await call_llm(prompt)
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
        response_text = await call_llm(prompt)
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

# ══════════════════════════════════════════════════════════════════════════
# Stage 2 — Hierarchical structuring (Acts -> Sequences -> Beats)
#
# Deliberately its own function, separate from Stage 3/4/5's per-scene detail
# extraction. Operates on Stage 1's already-parsed scene list (never the raw
# screenplay text) and never invents/renumbers a scene.
# ══════════════════════════════════════════════════════════════════════════

STAGE2_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "acts": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "act_number": {"type": "INTEGER"},
                    "title": {"type": "STRING"},
                    "sequences": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "sequence_title": {"type": "STRING"},
                                "scene_numbers": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                                "beats": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "beat_title": {"type": "STRING"},
                                            "scene_numbers": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                                            "beat_purpose": {"type": "STRING"},
                                        },
                                        "required": ["beat_title", "scene_numbers", "beat_purpose"],
                                    },
                                },
                            },
                            "required": ["sequence_title", "scene_numbers", "beats"],
                        },
                    },
                },
                "required": ["act_number", "title", "sequences"],
            },
        },
        # Not part of the spec's literal schema — carried forward internally
        # as context for the NEXT batch so continuity holds across the whole
        # screenplay without ever sending the full script in one call.
        "running_summary": {"type": "STRING"},
    },
    "required": ["acts", "running_summary"],
}


def _build_stage2_prompt(batch_scenes: List[Dict[str, Any]], running_summary: str, is_first: bool) -> str:
    scene_lines = []
    for s in batch_scenes:
        chars = ", ".join(s.get("characters_present") or []) or "None"
        action = (s.get("raw_action") or "").strip() or "(no action lines)"
        scene_lines.append(
            f"Scene {s['scene_number']}: {s.get('heading', '')}\nCharacters: {chars}\nAction: {action}"
        )
    scenes_block = "\n\n".join(scene_lines)

    context_block = (
        "This is the BEGINNING of the screenplay — there is no prior context."
        if is_first
        else f"STORY SO FAR (summary of everything structured before this batch):\n{running_summary}"
    )

    return f"""
Act as a professional script supervisor breaking a screenplay into its hierarchical
Acts -> Sequences -> Beats structure, working ONLY from the real parsed scene data below
(never invent, skip, or renumber a scene).

{context_block}

NEW SCENES TO STRUCTURE (scene numbers {batch_scenes[0]['scene_number']}-{batch_scenes[-1]['scene_number']}):
{scenes_block}

Rules:
- Use ONLY the scene numbers listed above. Every one of them must appear in exactly one beat's scene_numbers list.
- If this batch continues the same act that was still open at the end of the story so far, reuse that
  exact act_number and title so it can be merged; otherwise start a new act_number.
- Return STRICT JSON only, matching exactly this shape, no markdown fences, no commentary:
{{
  "acts": [{{
    "act_number": 1,
    "title": "string",
    "sequences": [{{
      "sequence_title": "string",
      "scene_numbers": [1, 2, 3],
      "beats": [{{"beat_title": "string", "scene_numbers": [1, 2], "beat_purpose": "string"}}]
    }}]
  }}],
  "running_summary": "2-4 sentence summary of the story through the end of this batch, to carry forward as context for the next batch"
}}
"""


def _validate_stage2_structure(data: Any, valid_scene_numbers: set) -> List[str]:
    """Returns a list of human-readable errors (empty if valid). Used to drive
    the repair loop — errors get appended to the re-prompt verbatim."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Response is not a JSON object."]

    acts = data.get("acts")
    if not isinstance(acts, list) or not acts:
        return ["'acts' must be a non-empty list."]

    seen_scene_numbers = set()
    for i, act in enumerate(acts):
        if not isinstance(act, dict):
            errors.append(f"acts[{i}] is not an object.")
            continue
        if not isinstance(act.get("act_number"), int):
            errors.append(f"acts[{i}].act_number must be an integer.")
        if not act.get("title"):
            errors.append(f"acts[{i}].title must be a non-empty string.")

        sequences = act.get("sequences")
        if not isinstance(sequences, list) or not sequences:
            errors.append(f"acts[{i}].sequences must be a non-empty list.")
            continue

        for j, seq in enumerate(sequences):
            if not isinstance(seq, dict):
                errors.append(f"acts[{i}].sequences[{j}] is not an object.")
                continue
            if not seq.get("sequence_title"):
                errors.append(f"acts[{i}].sequences[{j}].sequence_title must be non-empty.")

            beats = seq.get("beats")
            if not isinstance(beats, list) or not beats:
                errors.append(f"acts[{i}].sequences[{j}].beats must be a non-empty list.")
                continue

            for k, beat in enumerate(beats):
                if not isinstance(beat, dict):
                    errors.append(f"acts[{i}].sequences[{j}].beats[{k}] is not an object.")
                    continue
                if not beat.get("beat_title"):
                    errors.append(f"acts[{i}].sequences[{j}].beats[{k}].beat_title must be non-empty.")
                if not beat.get("beat_purpose"):
                    errors.append(f"acts[{i}].sequences[{j}].beats[{k}].beat_purpose must be non-empty.")

                scene_numbers = beat.get("scene_numbers")
                if not isinstance(scene_numbers, list) or not scene_numbers:
                    errors.append(f"acts[{i}].sequences[{j}].beats[{k}].scene_numbers must be a non-empty list.")
                    continue
                for sn in scene_numbers:
                    if not isinstance(sn, int):
                        errors.append(f"scene_numbers must all be integers, got {sn!r}.")
                    elif sn not in valid_scene_numbers:
                        errors.append(
                            f"scene_numbers references scene {sn}, which is not in this batch "
                            f"({sorted(valid_scene_numbers)})."
                        )
                    else:
                        seen_scene_numbers.add(sn)

    missing = valid_scene_numbers - seen_scene_numbers
    if missing:
        errors.append(f"These scene numbers from the batch were never assigned to a beat: {sorted(missing)}.")
    if not data.get("running_summary"):
        errors.append("'running_summary' must be a non-empty string.")
    return errors


def _fallback_stage2_batch(batch_scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic fallback if every LLM provider and every repair attempt
    fails — one beat per scene, clearly labeled, so the pipeline never just
    drops scenes rather than silently accepting malformed output."""
    beats = [{
        "beat_title": s.get("heading") or f"Scene {s['scene_number']}",
        "scene_numbers": [s["scene_number"]],
        "beat_purpose": "Auto-generated fallback beat (AI structuring unavailable).",
    } for s in batch_scenes]
    return {
        "acts": [{
            "act_number": 1,
            "title": f"Scenes {batch_scenes[0]['scene_number']}-{batch_scenes[-1]['scene_number']} (fallback)",
            "sequences": [{
                "sequence_title": "Auto-generated sequence (AI structuring unavailable)",
                "scene_numbers": [s["scene_number"] for s in batch_scenes],
                "beats": beats,
            }],
        }],
        "running_summary": "",
    }


async def _structure_stage2_batch(
    batch_scenes: List[Dict[str, Any]], running_summary: str, is_first: bool, max_retries: int = 2
) -> Dict[str, Any]:
    valid_scene_numbers = {s["scene_number"] for s in batch_scenes}
    base_prompt = _build_stage2_prompt(batch_scenes, running_summary, is_first)
    last_error = "no attempt made"

    for attempt in range(max_retries + 1):
        prompt = base_prompt if attempt == 0 else (
            f"{base_prompt}\n\nYour previous response was invalid for these reasons:\n"
            f"{last_error}\nReturn corrected JSON only, still matching the exact shape above."
        )
        try:
            response_text = await call_llm(prompt, response_schema=STAGE2_RESPONSE_SCHEMA)
        except Exception as e:
            last_error = f"Provider call raised an exception: {e}"
            continue
        if not response_text:
            last_error = "Received an empty response from all configured LLM providers."
            continue
        try:
            data = json.loads(re_clean_json(response_text))
        except Exception as e:
            last_error = f"Response was not valid JSON: {e}"
            continue

        errors = _validate_stage2_structure(data, valid_scene_numbers)
        if not errors:
            return data
        last_error = "; ".join(errors)

    logger.error(f"Stage 2 structuring failed after {max_retries} retries: {last_error}")
    return _fallback_stage2_batch(batch_scenes)


def _merge_stage2_acts(acts: List[Dict[str, Any]], new_acts: List[Dict[str, Any]]) -> None:
    for new_act in new_acts:
        if acts and acts[-1].get("act_number") == new_act.get("act_number"):
            acts[-1]["sequences"].extend(new_act.get("sequences", []))
        else:
            acts.append(new_act)


async def structure_screenplay(scenes: List[Dict[str, Any]], batch_size: int = 30) -> Dict[str, Any]:
    """
    Stage 2 entry point. Chunks Stage 1's flat scene list into act-sized
    windows (spec: 25-35 scenes/call — default 30) and structures them
    sequentially, carrying a running summary forward as context so the LLM
    keeps global continuity without ever seeing the whole screenplay at once.
    Returns {"acts": [...]} ready to store on Project.screenplay_structure.
    """
    if not scenes:
        return {"acts": []}

    ordered = sorted(scenes, key=lambda s: s["scene_number"])
    batches = [ordered[i:i + batch_size] for i in range(0, len(ordered), batch_size)]

    acts: List[Dict[str, Any]] = []
    running_summary = ""
    for batch_index, batch in enumerate(batches):
        result = await _structure_stage2_batch(batch, running_summary, is_first=(batch_index == 0))
        running_summary = result.get("running_summary") or running_summary
        _merge_stage2_acts(acts, result.get("acts", []))

    return {"acts": acts}


# ══════════════════════════════════════════════════════════════════════════
# Stage 3 — Scene understanding
#
# Extracts emotion/conflict/objects/visual-emphasis/continuity per scene.
# Deliberately does NOT re-derive characters/location/time — those are
# Stage 1's deterministic ground truth (parser.py); Stage 3 only adds the
# genuinely-new fields and treats Stage 1's output as read-only input.
# ══════════════════════════════════════════════════════════════════════════

STAGE3_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "scene_number": {"type": "INTEGER"},
                    "action_summary": {"type": "STRING"},
                    "emotion": {"type": "STRING"},
                    "conflict": {"type": "STRING"},  # empty string, not null, when there is none
                    "key_objects": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "visual_emphasis": {"type": "STRING"},
                    "continuity_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["scene_number", "action_summary", "emotion", "conflict", "visual_emphasis"],
            },
        },
    },
    "required": ["scenes"],
}


def _build_stage3_prompt(batch_scenes: List[Dict[str, Any]], prior_context: str) -> str:
    scene_lines = []
    for s in batch_scenes:
        chars = ", ".join(s.get("characters_present") or []) or "None"
        action = (s.get("raw_action") or "").strip() or "(no action lines)"
        dialogue = s.get("raw_dialogue") or []
        dialogue_preview = "; ".join(f"{d.get('character')}: {(d.get('content') or '')[:80]}" for d in dialogue[:3]) or "(no dialogue)"
        scene_lines.append(
            f"Scene {s['scene_number']}: {s.get('heading', '')}\n"
            f"Location: {s.get('location') or 'Unknown'} | Time: {s.get('time_of_day') or 'Unspecified'}\n"
            f"Characters: {chars}\nAction: {action}\nKey dialogue: {dialogue_preview}"
        )
    scenes_block = "\n\n".join(scene_lines)

    context_block = (
        "No earlier scenes to reference yet."
        if not prior_context
        else f"EARLIER SCENES (for continuity references only — e.g. recurring props/costume):\n{prior_context}"
    )

    return f"""
Act as a script supervisor doing detailed scene analysis for a director prepping storyboards.
For EACH scene below, extract: a short action summary, the dominant emotion, the core conflict
(empty string if there genuinely is none), important objects/props visible or referenced, what
the camera should visually emphasize, and any continuity requirements — props/costume/state that
must match an earlier scene (reference the earlier scene by number when relevant; omit entirely
if there are none, do not invent one).

{context_block}

SCENES TO ANALYZE (scene numbers {batch_scenes[0]['scene_number']}-{batch_scenes[-1]['scene_number']}):
{scenes_block}

Return STRICT JSON only, matching exactly this shape, no markdown fences, no commentary, with
EXACTLY one entry per scene number listed above (never skip or invent one):
{{
  "scenes": [
    {{
      "scene_number": 1,
      "action_summary": "string",
      "emotion": "string (e.g. excited, nostalgic, tense, joyful, fearful)",
      "conflict": "string, or an empty string if there is no conflict in this scene",
      "key_objects": ["string", "..."],
      "visual_emphasis": "string — what the camera should care about in this scene",
      "continuity_notes": ["string describing any prop/costume/state that must carry over"]
    }}
  ]
}}
"""


def _validate_stage3_structure(data: Any, valid_scene_numbers: set) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Response is not a JSON object."]

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return ["'scenes' must be a non-empty list."]

    seen = set()
    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            errors.append(f"scenes[{i}] is not an object.")
            continue

        sn = sc.get("scene_number")
        if not isinstance(sn, int):
            errors.append(f"scenes[{i}].scene_number must be an integer.")
        elif sn not in valid_scene_numbers:
            errors.append(f"scenes[{i}].scene_number={sn} is not in this batch ({sorted(valid_scene_numbers)}).")
        elif sn in seen:
            errors.append(f"scene_number {sn} appears more than once.")
        else:
            seen.add(sn)

        if not sc.get("action_summary"):
            errors.append(f"scenes[{i}].action_summary must be a non-empty string.")
        if not sc.get("emotion"):
            errors.append(f"scenes[{i}].emotion must be a non-empty string.")
        if not sc.get("visual_emphasis"):
            errors.append(f"scenes[{i}].visual_emphasis must be a non-empty string.")
        if "conflict" in sc and not isinstance(sc["conflict"], str):
            errors.append(f"scenes[{i}].conflict must be a string (use '' for none).")
        if "key_objects" in sc and not isinstance(sc["key_objects"], list):
            errors.append(f"scenes[{i}].key_objects must be a list.")
        if "continuity_notes" in sc and not isinstance(sc["continuity_notes"], list):
            errors.append(f"scenes[{i}].continuity_notes must be a list.")

    missing = valid_scene_numbers - seen
    if missing:
        errors.append(f"These scene numbers were never analyzed: {sorted(missing)}.")
    return errors


def _fallback_stage3_batch(batch_scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic fallback if every LLM provider and every repair attempt
    fails — never leaves a scene without an understanding record."""
    scenes = []
    for s in batch_scenes:
        action = (s.get("raw_action") or "").strip()
        scenes.append({
            "scene_number": s["scene_number"],
            "action_summary": (action[:200] if action else "No action recorded (AI understanding unavailable)."),
            "emotion": "neutral",
            "conflict": "",
            "key_objects": [],
            "visual_emphasis": "General coverage of the scene.",
            "continuity_notes": [],
        })
    return {"scenes": scenes}


async def _understand_stage3_batch(
    batch_scenes: List[Dict[str, Any]], prior_context: str, max_retries: int = 2
) -> Dict[str, Any]:
    valid_scene_numbers = {s["scene_number"] for s in batch_scenes}
    base_prompt = _build_stage3_prompt(batch_scenes, prior_context)
    last_error = "no attempt made"

    for attempt in range(max_retries + 1):
        prompt = base_prompt if attempt == 0 else (
            f"{base_prompt}\n\nYour previous response was invalid for these reasons:\n"
            f"{last_error}\nReturn corrected JSON only, still matching the exact shape above."
        )
        try:
            response_text = await call_llm(prompt, response_schema=STAGE3_RESPONSE_SCHEMA)
        except Exception as e:
            last_error = f"Provider call raised an exception: {e}"
            continue
        if not response_text:
            last_error = "Received an empty response from all configured LLM providers."
            continue
        try:
            data = json.loads(re_clean_json(response_text))
        except Exception as e:
            last_error = f"Response was not valid JSON: {e}"
            continue

        errors = _validate_stage3_structure(data, valid_scene_numbers)
        if not errors:
            return data
        last_error = "; ".join(errors)

    logger.error(f"Stage 3 scene understanding failed after {max_retries} retries: {last_error}")
    return _fallback_stage3_batch(batch_scenes)


async def understand_scenes(
    scenes: List[Dict[str, Any]], batch_size: int = 8, initial_prior_context: str = ""
) -> Dict[int, Dict[str, Any]]:
    """
    Stage 3 entry point. Batches 5-10 scenes/call (default 8) per spec.
    Carries forward a compact per-scene index (heading + key objects, not
    full text) as continuity context, so a later batch can still correctly
    reference "same jacket as scene 4" even when scene 4 was in an earlier
    batch — without resending full scene text for every prior scene.
    Returns {scene_number: understanding_record}, ready to persist onto
    each Scene row's action_summary/emotion/conflict/key_objects/
    visual_emphasis/continuity_notes columns.
    """
    if not scenes:
        return {}

    ordered = sorted(scenes, key=lambda s: s["scene_number"])
    batches = [ordered[i:i + batch_size] for i in range(0, len(ordered), batch_size)]

    results: Dict[int, Dict[str, Any]] = {}
    prior_context_lines: List[str] = [initial_prior_context] if initial_prior_context else []
    for batch in batches:
        batch_result = await _understand_stage3_batch(batch, "\n".join(prior_context_lines))
        for sc in batch_result.get("scenes", []):
            results[sc["scene_number"]] = sc
        for s in batch:
            sc = results.get(s["scene_number"], {})
            objs = ", ".join(sc.get("key_objects") or []) or "none"
            prior_context_lines.append(f"Scene {s['scene_number']} ({s.get('heading', '')}): key objects = {objs}")

    return results


# ══════════════════════════════════════════════════════════════════════════
# Stage 4 + 5 — Automatic shot division + cinematography plan
#
# Spec combines these into one route (POST /scenes/{id}/shots/generate-plan).
# app/shot_planner.py's suggest_shot_plan() is the rules-first engine (a
# "strong prior" per spec); the LLM here reorders/trims/extends it and
# writes the full per-shot cinematography record + required `reasoning`.
# ══════════════════════════════════════════════════════════════════════════

STAGE45_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "shots": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "shot_type": {"type": "STRING", "enum": SHOT_TYPES},
                    "reasoning": {"type": "STRING"},
                    "shot_size": {"type": "STRING"},
                    "camera_angle": {"type": "STRING"},
                    "lens_mm": {"type": "INTEGER"},
                    "camera_height": {"type": "STRING"},
                    "movement": {"type": "STRING"},
                    "framing": {"type": "STRING"},
                    "composition_notes": {"type": "STRING"},
                    "lighting": {
                        "type": "OBJECT",
                        "properties": {
                            "key": {"type": "STRING"},
                            "fill": {"type": "STRING"},
                            "backlight": {"type": "STRING"},
                            "practicals": {"type": "STRING"},
                            "quality": {"type": "STRING"},
                            "direction": {"type": "STRING"},
                            "intensity": {"type": "STRING"},
                            "color_temp_k": {"type": "INTEGER"},
                        },
                        "required": ["key", "quality", "color_temp_k"],
                    },
                    "mood": {"type": "STRING"},
                    "color_palette": {"type": "STRING"},
                    "contrast": {"type": "STRING"},
                    "depth_of_field": {"type": "STRING"},
                    "perspective_notes": {"type": "STRING"},
                },
                "required": ["shot_type", "reasoning", "shot_size", "camera_angle", "lens_mm", "movement", "lighting"],
            },
        },
    },
    "required": ["shots"],
}


def _build_stage45_prompt(scene: Dict[str, Any], rule_suggestions: List[Dict[str, str]]) -> str:
    chars = ", ".join(scene.get("characters_present") or []) or "None"
    action = (scene.get("raw_action") or "").strip() or "(no action lines)"
    emotion = scene.get("emotion") or "unspecified"
    conflict = scene.get("conflict") or "none"
    visual_emphasis = scene.get("visual_emphasis") or "unspecified"
    key_objects = ", ".join(scene.get("key_objects") or []) or "none"

    rules_block = "\n".join(f"- {s['shot_type']}: {s['rule_reasoning']}" for s in rule_suggestions) or \
        "(no strong rule-based suggestions — use your judgment)"
    shot_types_list = ", ".join(SHOT_TYPES)

    return f"""
Act as a director of photography breaking a scene into shots for a storyboard.

SCENE:
Heading: {scene.get('heading', '')}
Characters: {chars}
Action: {action}
Key objects: {key_objects}
Dominant emotion: {emotion}
Conflict: {conflict}
Visual emphasis: {visual_emphasis}

RULE-BASED SHOT SUGGESTIONS (a strong starting prior — reorder, merge, trim, or extend by at
most 2 shots if genuinely needed, but stay close to this list and its intent):
{rules_block}

For EACH final shot, produce a full cinematography plan. shot_type MUST be exactly one of:
{shot_types_list}

Derive lens_mm/camera_angle sensibly from shot_type (wide~24-35mm, medium~35-50mm,
close-up~50-85mm, extreme close-up~85-100mm+) but adjust based on the scene's mood/emotion
above. reasoning must explain, in one sentence, WHY this shot exists — never leave it empty.

Return STRICT JSON only, matching exactly this shape, no markdown fences, no commentary:
{{
  "shots": [
    {{
      "shot_type": "string (from the list above)",
      "reasoning": "string",
      "shot_size": "string (e.g. 'Wide Shot', 'Close-Up')",
      "camera_angle": "Eye Level | Low | High | Dutch",
      "lens_mm": 35,
      "camera_height": "string",
      "movement": "Static | Pan | Tilt | Dolly | Handheld | Push-In",
      "framing": "string",
      "composition_notes": "string",
      "lighting": {{
        "key": "string", "fill": "string", "backlight": "string",
        "practicals": "string", "quality": "Hard | Soft",
        "direction": "string", "intensity": "string", "color_temp_k": 5600
      }},
      "mood": "string",
      "color_palette": "string",
      "contrast": "Low | Medium | High",
      "depth_of_field": "Shallow | Deep",
      "perspective_notes": "string"
    }}
  ]
}}
"""


def _validate_stage45_structure(data: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Response is not a JSON object."]

    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        return ["'shots' must be a non-empty list."]

    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{i}] is not an object.")
            continue
        if shot.get("shot_type") not in SHOT_TYPES:
            errors.append(f"shots[{i}].shot_type must be one of {SHOT_TYPES}, got {shot.get('shot_type')!r}.")
        if not shot.get("reasoning"):
            errors.append(f"shots[{i}].reasoning must be a non-empty string.")
        if not shot.get("shot_size"):
            errors.append(f"shots[{i}].shot_size must be a non-empty string.")
        if not shot.get("camera_angle"):
            errors.append(f"shots[{i}].camera_angle must be a non-empty string.")
        if not isinstance(shot.get("lens_mm"), int):
            errors.append(f"shots[{i}].lens_mm must be an integer.")
        if not shot.get("movement"):
            errors.append(f"shots[{i}].movement must be a non-empty string.")
        lighting = shot.get("lighting")
        if not isinstance(lighting, dict) or not lighting.get("key"):
            errors.append(f"shots[{i}].lighting must be an object with at least a 'key' field.")

    return errors


def _fallback_stage45_plan(rule_suggestions: List[Dict[str, str]]) -> Dict[str, Any]:
    """Pure rules + defaults, no LLM involved — always available, always
    produces a complete, non-empty plan with a real `reasoning` per shot."""
    shots = []
    for s in rule_suggestions:
        defaults = default_cinematography_for_shot_type(s["shot_type"])
        shots.append({
            "shot_type": s["shot_type"],
            "reasoning": s["rule_reasoning"],
            "shot_size": f"{s['shot_type']} Shot",
            "camera_angle": defaults["camera_angle"],
            "lens_mm": defaults["lens_mm"],
            "camera_height": "Eye Level",
            "movement": "Static",
            "framing": "Standard framing.",
            "composition_notes": "Auto-generated fallback composition (AI cinematography unavailable).",
            "lighting": {
                "key": "Soft key light", "fill": "Ambient fill", "backlight": "",
                "practicals": "", "quality": "Soft", "direction": "Front",
                "intensity": "Medium", "color_temp_k": 5600,
            },
            "mood": "Neutral",
            "color_palette": "Natural",
            "contrast": "Medium",
            "depth_of_field": defaults["depth_of_field"],
            "perspective_notes": "",
        })
    return {"shots": shots}


async def _generate_shot_plan_llm(
    scene: Dict[str, Any], rule_suggestions: List[Dict[str, str]], max_retries: int = 2
) -> Dict[str, Any]:
    base_prompt = _build_stage45_prompt(scene, rule_suggestions)
    last_error = "no attempt made"

    for attempt in range(max_retries + 1):
        prompt = base_prompt if attempt == 0 else (
            f"{base_prompt}\n\nYour previous response was invalid for these reasons:\n"
            f"{last_error}\nReturn corrected JSON only, still matching the exact shape above."
        )
        try:
            response_text = await call_llm(prompt, response_schema=STAGE45_RESPONSE_SCHEMA)
        except Exception as e:
            last_error = f"Provider call raised an exception: {e}"
            continue
        if not response_text:
            last_error = "Received an empty response from all configured LLM providers."
            continue
        try:
            data = json.loads(re_clean_json(response_text))
        except Exception as e:
            last_error = f"Response was not valid JSON: {e}"
            continue

        errors = _validate_stage45_structure(data)
        if not errors:
            return data
        last_error = "; ".join(errors)

    logger.error(f"Stage 4/5 shot planning failed after {max_retries} retries: {last_error}")
    return _fallback_stage45_plan(rule_suggestions)


async def generate_shot_plan(scene: Dict[str, Any], is_first_scene_at_location: bool = False) -> List[Dict[str, Any]]:
    """
    Stage 4 + 5 entry point (spec's combined route:
    POST /scenes/{id}/shots/generate-plan). Runs the rules-first engine for
    a strong prior, then has the LLM refine shot_type/order and produce a
    full cinematography record per shot. `scene` should carry Stage 1 + 3
    output (raw_action, characters_present, key_objects, emotion, conflict,
    visual_emphasis). Falls back to pure rules + defaults if every LLM
    attempt fails — never returns an empty plan or a shot without reasoning.
    """
    rule_suggestions = suggest_shot_plan(scene, is_first_scene_at_location)
    result = await _generate_shot_plan_llm(scene, rule_suggestions)
    return result.get("shots", [])


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
        response_text = await call_llm(prompt)
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


# ══════════════════════════════════════════════════════════════════════════
# Stage 10 — natural-language shot editor
#
# Translates an instruction like "make this a low-angle shot" into a
# structured diff against ONLY the fields that should change, so the
# caller can apply it and re-queue Stage 7 for just that one shot.
# ══════════════════════════════════════════════════════════════════════════

VALID_EDIT_FIELDS = {
    "shot_type", "shot_size", "angle", "lens_mm", "movement", "camera_height",
    "framing", "composition_notes", "contrast", "depth_of_field",
    "perspective_notes", "color_palette", "mood", "day_night",
}

EDIT_DIFF_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "shot_type": {"type": "STRING", "enum": SHOT_TYPES},
        "shot_size": {"type": "STRING"},
        "angle": {"type": "STRING"},
        "lens_mm": {"type": "INTEGER"},
        "movement": {"type": "STRING"},
        "camera_height": {"type": "STRING"},
        "framing": {"type": "STRING"},
        "composition_notes": {"type": "STRING"},
        "contrast": {"type": "STRING"},
        "depth_of_field": {"type": "STRING"},
        "perspective_notes": {"type": "STRING"},
        "color_palette": {"type": "STRING"},
        "mood": {"type": "STRING"},
        "day_night": {"type": "STRING"},
    },
}


def _build_edit_diff_prompt(current_shot: Dict[str, Any], instruction: str) -> str:
    shot_types_list = ", ".join(SHOT_TYPES)
    return f"""
You are translating a director's natural-language editing instruction into a precise
structured change to a single shot's cinematography record.

CURRENT SHOT STATE:
{json.dumps(current_shot, indent=2)}

INSTRUCTION: "{instruction}"

Return STRICT JSON containing ONLY the fields that should actually change as a result of
this instruction — omit every field that stays the same. Valid fields: shot_type (one of
{shot_types_list}), shot_size, angle, lens_mm (integer), movement, camera_height, framing,
composition_notes, contrast, depth_of_field, perspective_notes, color_palette, mood, day_night.

Examples:
- "make this a low-angle shot" -> {{"angle": "Low"}}
- "use a 50mm lens" -> {{"lens_mm": 50}}
- "change to night" -> {{"day_night": "Night"}}
- "move camera behind the character" -> {{"angle": "Rear angle, over-the-shoulder-style", "camera_height": "Behind character, shoulder height"}}

Return ONLY the raw JSON object — no markdown fences, no commentary, no unchanged fields.
"""


def _validate_edit_diff(data: Any) -> List[str]:
    if not isinstance(data, dict):
        return ["Response is not a JSON object."]
    errors = []
    for key in data:
        if key not in VALID_EDIT_FIELDS:
            errors.append(f"Unknown field '{key}' in diff — valid fields are {sorted(VALID_EDIT_FIELDS)}.")
    if "shot_type" in data and data["shot_type"] not in SHOT_TYPES:
        errors.append(f"shot_type must be one of {SHOT_TYPES}, got {data['shot_type']!r}.")
    if "lens_mm" in data and not isinstance(data["lens_mm"], int):
        errors.append("lens_mm must be an integer.")
    if not data:
        errors.append("Diff must contain at least one changed field — the instruction produced no change.")
    return errors


def _fallback_edit_diff(instruction: str) -> Dict[str, Any]:
    """Deterministic keyword-based fallback if every LLM provider and every
    repair attempt fails — covers the spec's own worked examples so common
    edits still work with zero AI available."""
    text = instruction.lower()
    diff: Dict[str, Any] = {}

    if "dutch" in text:
        diff["angle"] = "Dutch"
    elif "low angle" in text or "low-angle" in text:
        diff["angle"] = "Low"
    elif "high angle" in text or "high-angle" in text:
        diff["angle"] = "High"
    elif "eye level" in text or "eye-level" in text:
        diff["angle"] = "Eye Level"

    lens_match = re.search(r"(\d+)\s*mm", text)
    if lens_match:
        diff["lens_mm"] = int(lens_match.group(1))

    if "night" in text:
        diff["day_night"] = "Night"
    elif "day" in text:
        diff["day_night"] = "Day"

    for movement, label in [("push-in", "Push-In"), ("push in", "Push-In"), ("handheld", "Handheld"),
                             ("dolly", "Dolly"), ("static", "Static"), ("pan", "Pan"), ("tilt", "Tilt")]:
        if movement in text:
            diff["movement"] = label
            break

    return diff


async def translate_shot_edit(current_shot: Dict[str, Any], instruction: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Stage 10 entry point. Returns a dict of ONLY the fields that should
    change (never the full record) — the caller applies it directly onto
    the Shot row and re-queues Stage 7 for that one shot.
    """
    base_prompt = _build_edit_diff_prompt(current_shot, instruction)
    last_error = "no attempt made"

    for attempt in range(max_retries + 1):
        prompt = base_prompt if attempt == 0 else (
            f"{base_prompt}\n\nYour previous response was invalid for these reasons:\n"
            f"{last_error}\nReturn corrected JSON only, still matching the exact shape above."
        )
        try:
            response_text = await call_llm(prompt, response_schema=EDIT_DIFF_RESPONSE_SCHEMA)
        except Exception as e:
            last_error = f"Provider call raised an exception: {e}"
            continue
        if not response_text:
            last_error = "Received an empty response from all configured LLM providers."
            continue
        try:
            data = json.loads(re_clean_json(response_text))
        except Exception as e:
            last_error = f"Response was not valid JSON: {e}"
            continue

        errors = _validate_edit_diff(data)
        if not errors:
            return data
        last_error = "; ".join(errors)

    logger.error(f"Stage 10 edit translation failed after {max_retries} retries: {last_error}")
    return _fallback_edit_diff(instruction)


async def draft_board_captions(scene_heading: str, scene_text: str, shots: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    """Stage 8: one-line board captions (+ the dialogue line heard in each shot).

    Only dialogue that literally appears in `scene_text` may be used -- the
    board must never put invented lines in a character's mouth. Returns
    {shot_number: {"caption": str, "dialogue": str}}; {} if the LLM fails.
    """
    shot_lines = "\n".join(
        f'- shot {s["shot_number"]} ({s.get("shot_size") or "shot"}): {s.get("reasoning") or ""} {s.get("notes") or ""}'.strip()
        for s in shots
    )
    prompt = f"""You write captions for a professional film storyboard sheet.
Scene: {scene_heading}
Scene text (action and dialogue):
{scene_text}

Shots:
{shot_lines}

For EACH shot return:
- "caption": what we see, present tense, at most 12 words, no camera jargon.
- "dialogue": the one line of dialogue heard during that shot, copied exactly from the scene text and formatted
  as NAME: “line” (curly quotes), or "" if no line fits. Never invent or paraphrase dialogue.

Return JSON only: {{"captions": [{{"shot_number": <int>, "caption": "<text>", "dialogue": "<text>"}}]}}"""
    raw = await call_llm(prompt)
    if not raw:
        return {}
    try:
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        return {int(c["shot_number"]): {"caption": str(c.get("caption") or "").strip(),
                                        "dialogue": str(c.get("dialogue") or "").strip()}
                for c in data.get("captions", []) if "shot_number" in c}
    except Exception as e:
        logger.warning(f"draft_board_captions: could not parse LLM output ({e})")
        return {}

