"""
Stage 4 — rules-first automatic shot division.

Deterministic, keyword/heuristic-driven shot suggestions that give the LLM
refinement layer (ai_service.generate_shot_plan, Stage 4b + Stage 5) a strong
prior per the spec: "Rules give a strong prior; the LLM adjusts and
justifies." Every suggestion carries a canonical shot_type and a plain-
English rule_reasoning the LLM can keep, rewrite, or discard.
"""
from typing import Any, Dict, List

# Canonical shot_type enum (spec section 2, Stage 4).
SHOT_TYPES = [
    "Wide Establishing", "Wide", "Medium", "Medium Close-Up", "Close-Up",
    "Extreme Close-Up", "Two-Shot", "Over-the-Shoulder", "POV", "Insert", "Cutaway",
]

# Stage 5 baseline lens/angle/DOF per shot_type — spec: "Derive lens/angle
# defaults from shot_type ... but let the LLM override based on scene
# mood/emotion." Used both as prompt context and as the deterministic
# fallback if every LLM provider fails.
DEFAULT_CINEMATOGRAPHY: Dict[str, Dict[str, Any]] = {
    "Wide Establishing": {"lens_mm": 24, "camera_angle": "Eye Level", "depth_of_field": "Deep"},
    "Wide":               {"lens_mm": 28, "camera_angle": "Eye Level", "depth_of_field": "Deep"},
    "Medium":             {"lens_mm": 35, "camera_angle": "Eye Level", "depth_of_field": "Medium"},
    "Medium Close-Up":    {"lens_mm": 50, "camera_angle": "Eye Level", "depth_of_field": "Shallow"},
    "Close-Up":           {"lens_mm": 85, "camera_angle": "Eye Level", "depth_of_field": "Shallow"},
    "Extreme Close-Up":   {"lens_mm": 100, "camera_angle": "Eye Level", "depth_of_field": "Shallow"},
    "Two-Shot":           {"lens_mm": 35, "camera_angle": "Eye Level", "depth_of_field": "Medium"},
    "Over-the-Shoulder":  {"lens_mm": 50, "camera_angle": "Eye Level", "depth_of_field": "Shallow"},
    "POV":                {"lens_mm": 35, "camera_angle": "Eye Level", "depth_of_field": "Medium"},
    "Insert":             {"lens_mm": 70, "camera_angle": "Eye Level", "depth_of_field": "Shallow"},
    "Cutaway":            {"lens_mm": 50, "camera_angle": "Eye Level", "depth_of_field": "Medium"},
}

ARRIVAL_KEYWORDS = ["arrives", "pulls up", "pulls into", "walks in", "walks into", "enters", "rolls up", "drives up", "steps out", "gets off"]
VEHICLE_KEYWORDS = ["bike", "motorbike", "motorcycle", "car", "bus", "truck", "scooter", "van", "vehicle", "road", "highway", "drives", "rides", "riding"]
PHONE_KEYWORDS = ["phone", "call", "dials", "rings", "calling"]
INTENSE_EMOTIONS = {
    "tense", "fearful", "heartbroken", "devastated", "furious", "angry", "emotional",
    "nostalgic", "excited", "anxious", "grief", "sad", "afraid", "terrified", "joyful",
    "elated", "desperate", "panicked",
}


def _contains_any(text: str, keywords: List[str]) -> bool:
    text_l = (text or "").lower()
    return any(kw in text_l for kw in keywords)


def default_cinematography_for_shot_type(shot_type: str) -> Dict[str, Any]:
    return dict(DEFAULT_CINEMATOGRAPHY.get(shot_type, DEFAULT_CINEMATOGRAPHY["Medium"]))


def suggest_shot_plan(scene: Dict[str, Any], is_first_scene_at_location: bool, max_shots: int = 8) -> List[Dict[str, str]]:
    """
    Returns an ordered list of {"shot_type", "rule_reasoning"} — the rules-
    first prior. `scene` is a dict carrying at least raw_action,
    key_objects, characters_present, emotion, conflict (Stage 1 + 3 output).
    """
    action = scene.get("raw_action") or ""
    key_objects = scene.get("key_objects") or []
    key_objects_text = " ".join(key_objects)
    characters = scene.get("characters_present") or []
    emotion = (scene.get("emotion") or "").lower()
    conflict = scene.get("conflict") or ""
    num_chars = len(characters)

    is_phone_call = _contains_any(action, PHONE_KEYWORDS) or _contains_any(key_objects_text, PHONE_KEYWORDS)
    is_arrival = _contains_any(action, ARRIVAL_KEYWORDS)
    is_vehicle_action = _contains_any(action, VEHICLE_KEYWORDS) or _contains_any(key_objects_text, VEHICLE_KEYWORDS)
    is_group = num_chars >= 3
    is_intense_emotion = emotion in INTENSE_EMOTIONS
    has_conflict = bool(conflict.strip())

    suggestions: List[Dict[str, str]] = []

    # 1. Establishing — new location or an arrival beat.
    if is_first_scene_at_location or is_arrival:
        suggestions.append({"shot_type": "Wide Establishing", "rule_reasoning": "Establishes a new location/arrival before moving into coverage."})

    # 2. Action/movement coverage.
    if is_vehicle_action:
        suggestions.append({"shot_type": "Wide", "rule_reasoning": "Wide coverage of the vehicle/movement in its environment."})
        suggestions.append({"shot_type": "Medium", "rule_reasoning": "Medium coverage tracking the movement/action."})
        suggestions.append({"shot_type": "Insert", "rule_reasoning": "Insert on the vehicle/prop detail referenced in the action."})

    # 3. Phone call — intercut CUs + insert, optional split-frame two-shot.
    if is_phone_call:
        for ch in characters[:2]:
            suggestions.append({"shot_type": "Close-Up", "rule_reasoning": f"Close-up on {ch} during the phone conversation."})
        suggestions.append({"shot_type": "Insert", "rule_reasoning": "Insert on the phone/hands to punctuate the call."})
        if num_chars >= 2:
            suggestions.append({"shot_type": "Two-Shot", "rule_reasoning": "Optional split-frame two-shot showing both callers."})

    # 4. Group / friends-arrive coverage.
    if is_group and not is_phone_call:
        suggestions.append({"shot_type": "Wide", "rule_reasoning": "Wide/two-shot establishing the group together."})
        suggestions.append({"shot_type": "Medium", "rule_reasoning": "Medium two-shot covering the group's interaction."})
        for ch in characters[:3]:
            suggestions.append({"shot_type": "Close-Up", "rule_reasoning": f"Reaction close-up on {ch}."})

    # 5. Conflict beat — OTS + two-shot.
    if has_conflict:
        suggestions.append({"shot_type": "Over-the-Shoulder", "rule_reasoning": f"OTS to frame the conflict: {conflict}"})
        suggestions.append({"shot_type": "Two-Shot", "rule_reasoning": "Two-shot holding both sides of the conflict in frame."})

    # 6. Emotional beat — push toward CU/ECU.
    if is_intense_emotion:
        suggestions.append({"shot_type": "Close-Up", "rule_reasoning": f"Push to a close-up to carry the scene's {emotion} emotion."})

    # 7. Baseline dialogue coverage if nothing more specific matched.
    if not suggestions and num_chars >= 2:
        suggestions.append({"shot_type": "Two-Shot", "rule_reasoning": "Baseline two-shot coverage for the scene's dialogue."})
        for ch in characters[:2]:
            suggestions.append({"shot_type": "Close-Up", "rule_reasoning": f"Close-up on {ch} for dialogue coverage."})

    # 8. Single-character / quiet-scene fallback.
    if not suggestions:
        suggestions.append({"shot_type": "Medium", "rule_reasoning": "Baseline medium coverage of the scene."})
        if num_chars == 1:
            suggestions.append({"shot_type": "Close-Up", "rule_reasoning": f"Close-up on {characters[0]}."})

    # De-dup exact repeats (preserve order), then cap.
    seen = set()
    deduped = []
    for s in suggestions:
        key = (s["shot_type"], s["rule_reasoning"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped[:max_shots]


# Shot types that inherently involve the whole cast present in the scene,
# used by infer_characters_in_shot() below when no name is mentioned by name.
_GROUP_SHOT_TYPES = {"Wide Establishing", "Wide", "Two-Shot", "Medium"}


def infer_characters_in_shot(shot_type: str, reasoning: str, scene_characters: List[str]) -> List[str]:
    """
    Stage 7 needs to know which named characters actually appear in a given
    shot (a subset of the scene's full cast) to route it through USO's
    character-consistency conditioning. Looks for character names mentioned
    by name in the shot's reasoning text (both this rules engine's own
    rule_reasoning and the LLM's final reasoning consistently name-check
    characters — see ai_service._build_stage45_prompt); falls back to the
    full scene cast for shot types that inherently involve everyone present,
    or to a single best guess otherwise.
    """
    if not scene_characters:
        return []
    reasoning_lower = (reasoning or "").lower()
    mentioned = [c for c in scene_characters if c.lower() in reasoning_lower]
    if mentioned:
        return mentioned
    if shot_type in _GROUP_SHOT_TYPES:
        return list(scene_characters)
    return scene_characters[:1]
