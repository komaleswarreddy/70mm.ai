import logging
from typing import Dict, Any, List
from app.rag.retriever import CinematicRetriever

logger = logging.getLogger(__name__)

class CinematicRAGEngine:
    def __init__(self):
        self.retriever = CinematicRetriever()

    async def answer_screenplay_query(self, query: str) -> Dict[str, Any]:
        """
        Queries the vector index database, fetches context, and returns answer + citations.
        """
        logger.info(f"RAG engine processing query: {query}")
        contexts = self.retriever.retrieve_relevant_context(query)
        
        # If a live LLM (Groq) is configured it could summarize the contexts;
        # Otherwise we formulate a structured mock synthesis.
        formatted_results = []
        for ctx in contexts:
            formatted_results.append({
                "book": ctx["book"],
                "author": ctx["author"],
                "chapter": ctx["chapter"],
                "page": ctx["page"],
                "text": ctx["text"],
                "score": ctx["score"]
            })
            
        return {
            "query": query,
            "results": formatted_results
        }
