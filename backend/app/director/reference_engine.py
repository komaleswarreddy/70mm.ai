import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ReferenceEngine:
    def __init__(self):
        self.movie_stills_db = [
            {
                "director": "Villeneuve",
                "movie": "Dune",
                "image_url": "https://images.unsplash.com/photo-1547483238-f400e65ccd56?w=400&q=80",
                "notes": "Low contrast desert silhouettes representing isolation."
            },
            {
                "director": "Nolan",
                "movie": "Oppenheimer",
                "image_url": "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=400&q=80",
                "notes": "Extreme high scale close up capturing dramatic micro expressions."
            },
            {
                "director": "Kubrick",
                "movie": "2001: A Space Odyssey",
                "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&q=80",
                "notes": "Mathematical symmetrical hallway perspective."
            }
        ]

    def get_stills_by_director(self, director: str) -> List[Dict[str, Any]]:
        logger.info(f"Retrieving reference stills for director: {director}")
        return [still for still in self.movie_stills_db if still["director"].lower() == director.lower()]
