import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DIRECTOR_PROFILES = {
    "Nolan": {
        "lens": "80mm IMAX / 70mm anamorphic",
        "composition": "Centered symmetry with high scale foreground depth, minimal rule of thirds usage.",
        "blocking": "Subject moving rapidly towards camera; volumetric backlighting on key figures.",
        "lighting": "High-contrast volumetric natural lights, cool blues and steel grays.",
        "reference_films": "Oppenheimer, Interstellar, Inception",
        "color_palette": "Deep grays, warm tungsten fire highlights, steel blue shadows"
    },
    "Villeneuve": {
        "lens": "35mm prime / Wide Arri Alexa",
        "composition": "Extreme wide shot with massive brutalist architecture dwarfing characters, strict leading lines.",
        "blocking": "Characters silhouetted standing static, looking out towards sweeping vistas.",
        "lighting": "Soft overcast ambient shadowless fill, side high-contrast profiles.",
        "reference_films": "Dune, Blade Runner 2049, Arrival",
        "color_palette": "Saturated sand ambers, dark slate, desaturated sky white"
    },
    "Kubrick": {
        "lens": "24mm wide angle prime",
        "composition": "Strict one-point perspective converging perfectly on the center subject, mathematical symmetry.",
        "blocking": "Slow tracking dolly moves, actors facing camera directly with Kubrick stare.",
        "lighting": "Diffused soft lighting from ceiling panels, high-key bright backgrounds.",
        "reference_films": "2001: A Space Odyssey, The Shining",
        "color_palette": "Sterile white, deep wood brown, single warning fire-engine red accent"
    },
    "Tarantino": {
        "lens": "35mm / Extreme low-angle trunk shot",
        "composition": "High-contrast Dutch tilts, whip pans, zoom lenses tracking fast movements.",
        "blocking": "Rapid character dialogue pacing, circular camera pans around table.",
        "lighting": "Hard warm high-contrast shadows, saturated primary colors overlays.",
        "reference_films": "Pulp Fiction, Django Unchained",
        "color_palette": "Saturated yellow gold, blood red, retro mustard browns"
    }
}

class DirectorModePro:
    def get_style_guidance(self, director_name: str) -> Dict[str, Any]:
        """
        Fetches lens, composition, blocking rules, and reference movies for director style.
        """
        logger.info(f"Retrieving Director Mode Pro profile for: {director_name}")
        profile = DIRECTOR_PROFILES.get(director_name, {
            "lens": "50mm prime standard",
            "composition": "Classic rule of thirds framing with clean master subject outline.",
            "blocking": "Static actors conversational framing, natural movements.",
            "lighting": "Soft natural key light with subtle fill shadow.",
            "reference_films": "Standard Cinematography Handbook",
            "color_palette": "Balanced natural colors"
        })
        return profile
