"""
Module 41: Cinematic Copilot Engine
Provides inline AI suggestions for scene writing, camera, blocking, and emotion.
"""
import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ─── Suggestion Templates ────────────────────────────────────────────────────

CAMERA_SUGGESTIONS = {
    "action": [
        "Match cut on motion — transition cut with a hand gesture or door close.",
        "Whip pan to reveal — hide the cut inside a fast camera movement.",
        "Dutch angle to heighten instability and psychological unease.",
    ],
    "dialogue": [
        "Two-shot → split to singles as tension rises — mirrors the emotional separation.",
        "Push-in slowly during the revelation — build oppressive intimacy.",
        "Over-the-shoulder reverse — anchor geography and power dynamics.",
    ],
    "transition": [
        "Match dissolve on a recurring object (clock, window, face).",
        "Jump cut to enforce disorientation or time fragmentation.",
        "Smash cut from silence to chaos — maximum contrast impact.",
    ],
}

BLOCKING_SUGGESTIONS = [
    "Place the dominant character upstage — use depth to reinforce hierarchy.",
    "Triangulate three characters; shift the apex to signal power transitions.",
    "Keep a physical barrier between characters during conflict — table, window, doorframe.",
    "Mirror movements between characters to subconsciously suggest a shared fate.",
    "Let the defeated character shrink spatially — back against wall, seated while others stand.",
]

EMOTION_ENHANCEMENTS = {
    "grief": "Lingering close-up on hands rather than face — the body reveals what tears conceal.",
    "joy": "Wide establishing shot — let the character exist freely within space.",
    "rage": "Rack focus from face to fist — let violence loom in shallow focus.",
    "fear": "High-angle shot looking down — reduce character to vulnerability.",
    "love": "Profile two-shot lit in golden hour — lean into classical romanticism.",
    "despair": "Low-key single source light — shadows devour the character.",
    "hope": "Motivated natural light creeping in — dawn as metaphor.",
    "betrayal": "Wide shot revealing isolation — pull back to show character alone in frame.",
}

SCENE_TRANSITIONS = [
    "Establish → approach → detail → reaction (4-shot scene build).",
    "Open on the aftermath, then flash back — in medias res structure.",
    "End scene mid-sentence to force audience participation.",
    "Use ambient sound from next scene before cutting — audio bridge.",
]


class CinematicCopilot:
    """
    Inline cinematic suggestions engine.
    Analyses context from the agent memory and current scene fragment,
    returning structured suggestions across multiple dimensions.
    """

    async def suggest(self, scene_fragment: str, memory=None) -> Dict[str, Any]:
        """
        Returns multi-dimensional suggestions for a given scene fragment.
        """
        from app import ai_service

        fragment_lower = scene_fragment.lower()

        # ── Determine scene type ─────────────────────────────────────────────
        if any(w in fragment_lower for w in ["says", "asks", "replies", "whispers", "shouts"]):
            scene_type = "dialogue"
        elif any(w in fragment_lower for w in ["runs", "fights", "chases", "crashes", "explodes"]):
            scene_type = "action"
        else:
            scene_type = "transition"

        # ── Detect dominant emotion ──────────────────────────────────────────
        detected_emotion = self._detect_emotion(fragment_lower)

        # ── Build AI-enhanced suggestion (with fallback) ─────────────────────
        ai_suggestion = await self._ai_scene_suggestion(scene_fragment, memory)

        # ── Assemble response ────────────────────────────────────────────────
        return {
            "scene_type": scene_type,
            "detected_emotion": detected_emotion,
            "camera_suggestions": CAMERA_SUGGESTIONS.get(scene_type, CAMERA_SUGGESTIONS["action"]),
            "blocking_suggestions": BLOCKING_SUGGESTIONS[:3],
            "emotion_enhancement": EMOTION_ENHANCEMENTS.get(detected_emotion, ""),
            "transition_options": SCENE_TRANSITIONS[:2],
            "ai_suggestion": ai_suggestion,
            "director_note": self._director_note(memory),
        }

    def _detect_emotion(self, text: str) -> str:
        emotion_keywords = {
            "grief": ["dies", "death", "loss", "tears", "mourns", "weeping"],
            "joy": ["laughs", "celebrates", "smiles", "cheers", "happy"],
            "rage": ["screams", "slams", "punches", "fury", "anger", "smashes"],
            "fear": ["trembles", "backs away", "hides", "terrified", "shaking"],
            "love": ["embraces", "kisses", "holds", "tenderly", "romantic"],
            "despair": ["hopeless", "give up", "nothing", "empty", "alone"],
            "hope": ["sunrise", "beginning", "new", "future", "together"],
            "betrayal": ["lied", "betrayed", "secret", "never trusted"],
        }
        for emotion, keywords in emotion_keywords.items():
            if any(k in text for k in keywords):
                return emotion
        return "neutral"

    async def _ai_scene_suggestion(self, fragment: str, memory) -> str:
        from app import ai_service

        context = ""
        if memory:
            context = f"Film: {memory.project_title}. Style: {memory.director_style}. Genre: {memory.genre}."

        prompt = f"""You are a senior script consultant and cinematographer.
{context}

Analyse the following scene fragment and provide ONE concise cinematic improvement suggestion (max 2 sentences):

SCENE FRAGMENT:
{fragment}

Return only the suggestion text. No labels, no JSON."""

        try:
            raw = await ai_service.call_gemini_api(prompt)
            if raw:
                return raw.strip()
        except Exception as e:
            logger.warning(f"Copilot AI suggestion failed: {e}")

        # Fallback
        return "Consider placing the character in a dynamic relationship with the environment — use architecture to reflect inner state."

    def _director_note(self, memory) -> str:
        if not memory:
            return ""
        style = getattr(memory, "director_style", "")
        notes = {
            "Kubrick": "Maintain symmetrical composition. Use the one-point perspective to trap characters in systems.",
            "Villeneuve": "Let silence carry weight. Slow the pace. Trust the audience to breathe with the film.",
            "Nolan": "Invert time or reveal. Plant an object in act one that resonates in act three.",
            "Wong Kar-Wai": "Blur the line between memory and present. Use colour temperature as emotional temperature.",
            "Coppola": "Family as microcosm of society. Every personal decision has geopolitical weight.",
            "Scorsese": "Voice-over as unreliable narrator. Energy of the streets must bleed into every frame.",
        }
        return notes.get(style, "Trust your instincts. Clarity of intention translates to clarity of image.")


# ─── Inline Copilot API Routes ───────────────────────────────────────────────

from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotRequest(BaseModel):
    scene_fragment: str
    project_id: Optional[str] = None
    director_style: Optional[str] = None


@router.post("/suggest")
async def copilot_suggest(req: CopilotRequest):
    """Returns inline cinematic suggestions for a scene fragment."""
    memory = None
    if req.project_id:
        from app.agent_coordinator import get_or_create_memory
        memory = get_or_create_memory(req.project_id)
        if req.director_style:
            memory.director_style = req.director_style

    copilot = CinematicCopilot()
    return await copilot.suggest(req.scene_fragment, memory)


@router.post("/agent-route")
async def agent_route_endpoint(
    agent_name: str = Body(...),
    user_input: str = Body(...),
    project_id: str = Body(...)
):
    """Universal agent routing endpoint."""
    from app.agent_coordinator import get_coordinator
    coordinator = get_coordinator()
    return await coordinator.route(agent_name, user_input, project_id)
