from typing import List, Dict, Any
from app.rag.embeddings import SentenceEmbeddingEngine
from app.rag.knowledge_loader import KnowledgeLoader

class CinematicRetriever:
    def __init__(self):
        self.embeddings = SentenceEmbeddingEngine()
        self.loader = KnowledgeLoader()
        self.chunks = self.loader.load_all_chunks()

    def retrieve_relevant_context(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        query_vec = self.embeddings.get_embedding(query)
        scored_chunks = []
        
        for chunk in self.chunks:
            chunk_vec = self.embeddings.get_embedding(chunk["text"])
            similarity = self.embeddings.compute_cosine_similarity(query_vec, chunk_vec)
            
            # Boost score if keywords match the title/book name
            keywords = query.lower().split()
            title_boost = 0.0
            if any(k in chunk["book"].lower() for k in keywords):
                title_boost = 0.15
            
            scored_chunks.append({
                "book": chunk["book"],
                "author": chunk["author"],
                "chapter": chunk["chapter"],
                "page": chunk["page"],
                "text": chunk["text"],
                "score": similarity + title_boost
            })
            
        # Sort by similarity score descending
        scored_chunks = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
