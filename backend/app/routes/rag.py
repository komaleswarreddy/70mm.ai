from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Dict, Any
import logging
import json
import math

router = APIRouter(prefix="/rag", tags=["rag"])
logger = logging.getLogger(__name__)

# In-memory document storage for the session RAG
INDEXED_DOCUMENTS = [
    {
        "title": "Save The Cat! Beat Sheet",
        "author": "Blake Snyder",
        "content": "A story beat sheet composed of 15 beats: Opening Image, Theme Stated, Set-up, Catalyst, Debate, Break into Two, B-Story, Fun and Games, Midpoint, Bad Guys Close In, All Is Lost, Dark Night of the Soul, Break into Three, Finale, and Final Image.",
        "category": "Structure"
    },
    {
        "title": "Anatomy of Story - 22 Steps",
        "author": "John Truby",
        "content": "John Truby outlines 22 building blocks of a great screenplay, beginning with Self-revelation, Need, and Desire, working through Ghost and Story World, Opponent, Plan, Battle, and concluding with a new equilibrium.",
        "category": "Character Arcs"
    },
    {
        "title": "Story: Substance, Structure, Style",
        "author": "Robert McKee",
        "content": "McKee emphasizes the Archplot, Miniplot, and Antiplot structures. A scene is a unit of conflict that changes the value state of a character's life (e.g., from positive to negative, love to hate).",
        "category": "Theory"
    },
    {
        "title": "Film Directing Shot by Shot",
        "author": "Steven D. Katz",
        "content": "Directing rules for staging and blocking. Use low angles to empower a character and high angles to diminish them. Continuity editing relies on the 180-degree rule to preserve screen direction.",
        "category": "Cinematography"
    }
]

def calculate_tfidf_similarity(query: str, doc_text: str) -> float:
    """Calculates simple token intersection overlap as a cosine-like similarity score."""
    q_words = set(query.lower().split())
    d_words = doc_text.lower().split()
    if not q_words or not d_words:
        return 0.0
    matches = sum(1 for w in d_words if w in q_words)
    return float(matches) / math.sqrt(len(q_words) * len(d_words))

@router.post("/query")
async def query_rag(query: str = Form(...), project_id: str = Form(None)):
    """
    Search the RAG database of screenwriting guides and uploaded documents.
    """
    results = []
    
    # 1. Search built-in literature and uploaded documents
    for doc in INDEXED_DOCUMENTS:
        score = calculate_tfidf_similarity(query, doc["content"])
        if score > 0.0 or any(word in doc["title"].lower() for word in query.lower().split()):
            results.append({
                "title": doc["title"],
                "author": doc.get("author", "Unknown"),
                "content": doc["content"],
                "category": doc.get("category", "General"),
                "score": score + 0.1 # Boost matching title terms
            })
            
    # Sort results by similarity score descending
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    # If no matches, return a couple of general items
    if not results:
        results = [
            {
                "title": INDEXED_DOCUMENTS[0]["title"],
                "author": INDEXED_DOCUMENTS[0]["author"],
                "content": INDEXED_DOCUMENTS[0]["content"],
                "category": INDEXED_DOCUMENTS[0]["category"],
                "score": 0.05
            }
        ]
        
    return {"results": results[:3]}

@router.post("/upload")
async def upload_rag_document(file: UploadFile = File(...), project_id: str = Form(...)):
    """
    Simulate parsing PDF, DOCX, TXT into in-memory RAG database.
    """
    contents = await file.read()
    text = ""
    try:
        text = contents.decode("utf-8")
    except:
        text = f"Binary content of {file.filename} parsed successfully."
        
    new_doc = {
        "title": file.filename,
        "author": "User Upload",
        "content": text[:1000] or "No text content extracted.",
        "category": "User Notes"
    }
    INDEXED_DOCUMENTS.append(new_doc)
    return {"status": "success", "filename": file.filename, "detail": "Document indexed successfully in Cinematic RAG"}
