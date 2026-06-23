import os
from typing import List, Dict, Any

class KnowledgeLoader:
    def __init__(self):
        # Local mock corpus for RAG sources
        self.library_sources = [
            {
                "book": "Save The Cat!",
                "author": "Blake Snyder",
                "chapter": "Chapter 3: Building the Beat Sheet",
                "page": 42,
                "text": "The Catalyst beat occurs at page 12 of a standard screenplay. It is the life-changing event that disrupts the protagonist's status quo, throwing them into the debate phase."
            },
            {
                "book": "Story: Substance, Structure, Style",
                "author": "Robert McKee",
                "chapter": "Chapter 6: Structure and Character",
                "page": 105,
                "text": "A scene changes a value condition of a character's life. If a scene ends with the character in the same value state as they started, the scene has no narrative reason to exist."
            },
            {
                "book": "The Anatomy of Story",
                "author": "John Truby",
                "chapter": "Chapter 2: The Premise and Character Need",
                "page": 88,
                "text": "The psychological weakness is the internal flaw holding the hero back. It is resolved only during the self-revelation at the climax of the narrative."
            },
            {
                "book": "Film Directing Shot by Shot",
                "author": "Steven D. Katz",
                "chapter": "Chapter 8: Staging and Framing",
                "page": 195,
                "text": "The 180-degree rule establishes screen direction. Crossing the axis of action causes spatial confusion for the audience unless a neutral shot is inserted."
            }
        ]

    def load_all_chunks(self) -> List[Dict[str, Any]]:
        return self.library_sources
