import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.rag.index")
def index_documents_background(project_id: str, file_path: str):
    """
    Parses and indexes large PDF/DOCX screenwriting guides.
    """
    logger.info(f"Background worker indexing RAG file {file_path} for project: {project_id}")
    import time
    time.sleep(1.5) # simulate indexing
    logger.info(f"Background worker finished indexing file {file_path}")
    return {"status": "success", "file_path": file_path}
