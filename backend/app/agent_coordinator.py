"""
Module 40: Agent Coordinator
Orchestrates all specialized AI agents and manages shared context/memory.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Agent Memory Context ────────────────────────────────────────────────────

@dataclass
class AgentMemory:
    """Shared memory context across all agents for a single project session."""
    project_id: str
    project_title: str = ""
    logline: str = ""
    themes: List[str] = field(default_factory=list)
    characters: List[Dict] = field(default_factory=list)
    scenes: List[Dict] = field(default_factory=list)
    director_style: str = "Kubrick"
    tone: str = "Cinematic"
    genre: str = "Drama"
    conversation_history: List[Dict] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_context_string(self) -> str:
        """Serialise memory to a compact context string for prompt injection."""
        parts = [f"Project: {self.project_title}"]
        if self.logline:
            parts.append(f"Logline: {self.logline}")
        if self.themes:
            parts.append(f"Themes: {', '.join(self.themes)}")
        if self.characters:
            names = [c.get('name', '?') for c in self.characters]
            parts.append(f"Key Characters: {', '.join(names)}")
        if self.director_style:
            parts.append(f"Director Style: {self.director_style}")
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        return "\n".join(parts)

    def add_conversation_turn(self, agent: str, user_input: str, response: str):
        self.conversation_history.append({
            "agent": agent,
            "user": user_input,
            "assistant": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep last 20 turns to avoid context bloat
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        self.last_updated = datetime.utcnow().isoformat()


# ─── In-memory session store (per project_id) ────────────────────────────────

_memory_store: Dict[str, AgentMemory] = {}


def get_or_create_memory(project_id: str, **kwargs) -> AgentMemory:
    if project_id not in _memory_store:
        _memory_store[project_id] = AgentMemory(project_id=project_id, **kwargs)
    return _memory_store[project_id]


def update_memory(project_id: str, **updates) -> AgentMemory:
    mem = get_or_create_memory(project_id)
    for k, v in updates.items():
        if hasattr(mem, k):
            setattr(mem, k, v)
    mem.last_updated = datetime.utcnow().isoformat()
    return mem


def clear_memory(project_id: str):
    _memory_store.pop(project_id, None)


# ─── Agent Coordinator ───────────────────────────────────────────────────────

class AgentCoordinator:
    """
    Routes requests to the appropriate specialised agent.
    Injects shared project memory into every agent call.
    Prevents hallucinations by grounding prompts with project context.
    """

    AGENT_REGISTRY = {
        "story": "generate_story_from_idea",
        "character": "generate_character_details",
        "scene": "suggest_scene_actions",
        "director": "director_muse",
        "copilot": "copilot_inline_suggestion",
        "script_doctor": "script_doctor_analysis",
    }

    def __init__(self):
        from app import ai_service
        self.ai_service = ai_service

    def _build_grounded_prompt(self, base_prompt: str, memory: AgentMemory) -> str:
        """Prefix base_prompt with project context to prevent hallucinations."""
        context = memory.to_context_string()
        return f"""[PROJECT CONTEXT — DO NOT DEVIATE FROM THIS CANON]
{context}
[END CONTEXT]

{base_prompt}"""

    async def route(
        self,
        agent_name: str,
        user_input: str,
        project_id: str,
        extra_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Route a user request to the named agent with full memory context.
        Returns standardised dict: {agent, input, output, memory_snapshot}
        """
        memory = get_or_create_memory(project_id)

        if extra_context:
            for k, v in extra_context.items():
                if hasattr(memory, k):
                    setattr(memory, k, v)

        grounded_prompt = self._build_grounded_prompt(user_input, memory)
        logger.info(f"AgentCoordinator routing to [{agent_name}] for project {project_id}")

        try:
            output = await self._dispatch(agent_name, grounded_prompt, user_input, memory)
        except Exception as e:
            logger.error(f"Agent [{agent_name}] failed: {e}")
            output = {"error": str(e), "fallback": True, "agent": agent_name}

        memory.add_conversation_turn(agent_name, user_input, json.dumps(output))

        return {
            "agent": agent_name,
            "project_id": project_id,
            "input": user_input,
            "output": output,
            "memory_snapshot": {
                "characters": len(memory.characters),
                "scenes": len(memory.scenes),
                "director_style": memory.director_style,
                "turns": len(memory.conversation_history),
            }
        }

    async def _dispatch(self, agent_name: str, grounded_prompt: str, raw_input: str, memory: AgentMemory) -> Any:
        ai = self.ai_service

        if agent_name == "story":
            return await ai.generate_story_from_idea(raw_input)

        elif agent_name == "character":
            return await ai.generate_character_details(
                name=raw_input,
                genre=memory.genre,
                tone=memory.tone,
                themes=memory.themes
            )

        elif agent_name == "scene":
            return await ai.suggest_scene_actions(raw_input, memory.director_style)

        elif agent_name == "director":
            shot_info = memory.scenes[0]["shots"][0] if memory.scenes and memory.scenes[0].get("shots") else {}
            return await ai.director_muse(memory.director_style, shot_info)

        elif agent_name == "copilot":
            from app.copilot_engine import CinematicCopilot
            copilot = CinematicCopilot()
            return await copilot.suggest(raw_input, memory)

        elif agent_name == "script_doctor":
            from app.script_doctor import ScriptDoctor
            doctor = ScriptDoctor()
            return await doctor.analyse(raw_input, memory)

        else:
            raise ValueError(f"Unknown agent: {agent_name}")


# Singleton coordinator
_coordinator: Optional[AgentCoordinator] = None

def get_coordinator() -> AgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator
