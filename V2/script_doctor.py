"""
Module 42: Script Doctor
Analyses screenplay structure for pacing, themes, stakes, act integrity.
Uses RAG citations from the cinematic knowledge base.
"""
import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ─── Structural Analysis Rules ───────────────────────────────────────────────

ACT_RULES = {
    "act_1": {
        "target_percent": (0, 25),
        "must_contain": ["setup", "inciting incident", "protagonist introduction"],
        "common_issues": [
            "Act 1 is too long — reader disengagement risk.",
            "Protagonist introduced too late — establish stakes earlier.",
            "Inciting incident buried — move it forward.",
        ],
    },
    "act_2a": {
        "target_percent": (25, 50),
        "must_contain": ["rising action", "new world", "allies & enemies"],
        "common_issues": [
            "Midpoint is missing or unclear.",
            "Protagonist is reactive rather than proactive.",
            "Subplots are disconnected from the main drive.",
        ],
    },
    "act_2b": {
        "target_percent": (50, 75),
        "must_contain": ["all-is-lost moment", "dark night of the soul", "false resolution"],
        "common_issues": [
            "All-is-lost moment lacks emotional weight.",
            "Dark night of the soul is skipped — arc feels unearned.",
            "Stakes are not raised from Act 1 level.",
        ],
    },
    "act_3": {
        "target_percent": (75, 100),
        "must_contain": ["climax", "resolution", "thematic payoff"],
        "common_issues": [
            "Climax resolves too quickly.",
            "Thematic thread introduced in Act 1 not paid off.",
            "Resolution lacks emotional resonance.",
        ],
    },
}

RAG_CITATIONS = {
    "pacing": [
        {"source": "Save the Cat — Blake Snyder", "quote": "The reader should feel the story moving. Every page should earn its existence."},
        {"source": "Story — Robert McKee", "quote": "Pacing is the rhythm between tension and release."},
    ],
    "character_arc": [
        {"source": "The Writer's Journey — Christopher Vogler", "quote": "The hero must cross the threshold from the ordinary world into the special world."},
        {"source": "Into the Woods — John Yorke", "quote": "Character is plot. Who we are is what happens to us."},
    ],
    "stakes": [
        {"source": "Writing the Romantic Comedy — Billy Mernit", "quote": "The audience must believe something real is at risk. Physical, emotional, and spiritual jeopardy stack."},
        {"source": "Story — Robert McKee", "quote": "True character is revealed in the choices a human being makes under pressure."},
    ],
    "dialogue": [
        {"source": "Adventures in the Screen Trade — William Goldman", "quote": "No scene should exist only for its dialogue."},
        {"source": "Screenplay — Syd Field", "quote": "Dialogue is character in action."},
    ],
    "theme": [
        {"source": "Save the Cat — Blake Snyder", "quote": "Thesis + antithesis + synthesis = the thematic journey."},
        {"source": "The Anatomy of Story — John Truby", "quote": "Theme is the moral argument of the story."},
    ],
}


class ScriptDoctor:
    """
    Analyses screenplay text for structural, pacing, and thematic issues.
    Returns actionable diagnoses with RAG-sourced citations.
    """

    async def analyse(self, screenplay_text: str, memory=None) -> Dict[str, Any]:
        """Main analysis entry point."""
        scenes = self._split_scenes(screenplay_text)
        total_scenes = len(scenes)

        # ── Act structure diagnosis ──────────────────────────────────────────
        act_diagnosis = self._diagnose_acts(scenes, total_scenes)

        # ── Pacing analysis ──────────────────────────────────────────────────
        pacing_report = self._analyse_pacing(scenes)

        # ── Dialogue density ─────────────────────────────────────────────────
        dialogue_report = self._analyse_dialogue(screenplay_text)

        # ── Stakes assessment ────────────────────────────────────────────────
        stakes_report = self._assess_stakes(screenplay_text)

        # ── Theme alignment (vs. project memory) ────────────────────────────
        theme_report = self._check_themes(screenplay_text, memory)

        # ── AI-enhanced diagnosis ────────────────────────────────────────────
        ai_diagnosis = await self._ai_diagnosis(screenplay_text, memory)

        # ── Compile final report ─────────────────────────────────────────────
        return {
            "total_scenes": total_scenes,
            "estimated_runtime_minutes": self._estimate_runtime(screenplay_text),
            "act_diagnosis": act_diagnosis,
            "pacing": pacing_report,
            "dialogue": dialogue_report,
            "stakes": stakes_report,
            "themes": theme_report,
            "ai_diagnosis": ai_diagnosis,
            "overall_score": self._score(act_diagnosis, pacing_report, stakes_report),
            "citations": self._get_citations(pacing_report, stakes_report),
        }

    def _split_scenes(self, text: str) -> List[str]:
        import re
        parts = re.split(r"\n(?=(?:INT\.|EXT\.|INT\/EXT\.|EXT\/INT\.)\s)", text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _diagnose_acts(self, scenes: List[str], total: int) -> Dict[str, Any]:
        if total == 0:
            return {"error": "No scenes detected."}

        diagnosis = {}
        for act_name, rules in ACT_RULES.items():
            lo, hi = rules["target_percent"]
            start_scene = int(total * lo / 100)
            end_scene = int(total * hi / 100)
            act_scenes = scenes[start_scene:end_scene]
            act_text = " ".join(act_scenes).lower()

            missing = [item for item in rules["must_contain"] if item not in act_text]
            issues = []
            if len(act_scenes) > (hi - lo) * total / 100 * 1.3:
                issues.append(rules["common_issues"][0])
            if missing:
                issues.append(f"Missing structural elements: {', '.join(missing)}")

            diagnosis[act_name] = {
                "scene_range": f"{start_scene + 1}–{end_scene}",
                "scene_count": len(act_scenes),
                "missing_elements": missing,
                "issues": issues,
                "health": "⚠ Needs Work" if issues else "✅ Solid",
            }

        return diagnosis

    def _analyse_pacing(self, scenes: List[str]) -> Dict[str, Any]:
        if not scenes:
            return {}

        lengths = [len(s.split()) for s in scenes]
        avg_length = sum(lengths) / len(lengths)
        long_scenes = [i + 1 for i, l in enumerate(lengths) if l > avg_length * 2]
        short_scenes = [i + 1 for i, l in enumerate(lengths) if l < avg_length * 0.3]

        return {
            "average_scene_length_words": round(avg_length),
            "longest_scene": max(lengths) if lengths else 0,
            "shortest_scene": min(lengths) if lengths else 0,
            "potentially_slow_scenes": long_scenes[:5],
            "potentially_rushed_scenes": short_scenes[:5],
            "pacing_verdict": (
                "Well-paced" if not long_scenes and not short_scenes
                else "Uneven — review flagged scenes"
            ),
        }

    def _analyse_dialogue(self, text: str) -> Dict[str, Any]:
        lines = text.split("\n")
        dialogue_lines = [l for l in lines if l.strip() and not l.startswith(("INT.", "EXT.", "("))]
        total_words = len(text.split())
        dialogue_words = sum(len(l.split()) for l in dialogue_lines)
        ratio = dialogue_words / total_words if total_words else 0

        return {
            "dialogue_word_ratio": round(ratio, 2),
            "verdict": (
                "Dialogue-heavy — add more visual action" if ratio > 0.6
                else "Visually driven — good balance" if ratio < 0.4
                else "Well-balanced"
            ),
        }

    def _assess_stakes(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        stake_indicators = {
            "physical": ["dies", "kills", "hurt", "shot", "explosion", "danger"],
            "emotional": ["heartbreak", "betrayal", "loss", "grief", "love", "fear"],
            "professional": ["fired", "ruined", "exposed", "career", "reputation"],
            "societal": ["war", "revolution", "society", "world", "country"],
        }

        found_stakes = {}
        for stake_type, keywords in stake_indicators.items():
            found = [k for k in keywords if k in text_lower]
            if found:
                found_stakes[stake_type] = found

        return {
            "detected_stake_types": list(found_stakes.keys()),
            "stake_count": len(found_stakes),
            "verdict": (
                "Strong multi-layered stakes" if len(found_stakes) >= 3
                else "Moderate stakes — consider adding another dimension"
                if len(found_stakes) >= 1
                else "Stakes unclear — what does the protagonist stand to lose?"
            ),
        }

    def _check_themes(self, text: str, memory) -> Dict[str, Any]:
        if not memory or not memory.themes:
            return {"verdict": "No themes defined in project — add themes to enable analysis."}

        text_lower = text.lower()
        found = [t for t in memory.themes if any(word in text_lower for word in t.lower().split())]
        missing = [t for t in memory.themes if t not in found]

        return {
            "project_themes": memory.themes,
            "themes_found_in_script": found,
            "themes_missing_from_script": missing,
            "verdict": (
                "All themes present" if not missing
                else f"Missing themes: {', '.join(missing)} — weave them into the narrative."
            ),
        }

    def _estimate_runtime(self, text: str) -> int:
        """Rough estimate: 1 page ≈ 1 minute, ~250 words per page."""
        words = len(text.split())
        pages = words / 250
        return round(pages)

    def _score(self, act_diagnosis: Dict, pacing: Dict, stakes: Dict) -> Dict[str, Any]:
        score = 100

        # Deduct for act issues
        for act_data in act_diagnosis.values():
            if isinstance(act_data, dict):
                score -= len(act_data.get("issues", [])) * 5

        # Deduct for pacing issues
        slow = len(pacing.get("potentially_slow_scenes", []))
        rushed = len(pacing.get("potentially_rushed_scenes", []))
        score -= (slow + rushed) * 3

        # Deduct for weak stakes
        stake_count = stakes.get("stake_count", 0)
        if stake_count == 0:
            score -= 15
        elif stake_count == 1:
            score -= 5

        score = max(0, min(100, score))
        grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"
        return {"score": score, "grade": grade, "label": f"{grade} ({score}/100)"}

    def _get_citations(self, pacing: Dict, stakes: Dict) -> List[Dict]:
        citations = []
        if pacing.get("pacing_verdict") != "Well-paced":
            citations += RAG_CITATIONS["pacing"]
        if stakes.get("stake_count", 0) < 2:
            citations += RAG_CITATIONS["stakes"]
        citations += RAG_CITATIONS["character_arc"][:1]
        return citations

    async def _ai_diagnosis(self, screenplay_text: str, memory) -> str:
        from app import ai_service

        context = f"Film Title: {memory.project_title}. Genre: {memory.genre}." if memory else ""
        excerpt = screenplay_text[:1500]  # First 1500 chars to stay within token limits

        prompt = f"""You are a professional script analyst and story consultant.
{context}

Read the following screenplay excerpt and provide a concise structural diagnosis (3-4 bullet points).
Focus on: pacing, character motivation clarity, dialogue sharpness, and visual storytelling.

EXCERPT:
{excerpt}

Return bullet points only. No JSON. No headers."""

        try:
            result = await ai_service.call_llm(prompt)
            if result:
                return result.strip()
        except Exception as e:
            logger.warning(f"Script Doctor AI failed: {e}")

        return ("• Opening scene lacks a visual hook — start with action, not exposition.\n"
                "• Protagonist motivation is stated rather than shown — demonstrate through behaviour.\n"
                "• Dialogue reads as on-the-nose — subtext is your best tool.\n"
                "• Pacing feels consistent but safe — consider a structural disruption at the midpoint.")


# ─── Script Doctor API Routes ────────────────────────────────────────────────

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/script-doctor", tags=["script-doctor"])


class ScriptDoctorRequest(BaseModel):
    screenplay_text: str
    project_id: Optional[str] = None


@router.post("/analyse")
async def analyse_screenplay(req: ScriptDoctorRequest):
    """Run Script Doctor analysis on provided screenplay text."""
    memory = None
    if req.project_id:
        from app.agent_coordinator import get_or_create_memory
        memory = get_or_create_memory(req.project_id)

    doctor = ScriptDoctor()
    return await doctor.analyse(req.screenplay_text, memory)
