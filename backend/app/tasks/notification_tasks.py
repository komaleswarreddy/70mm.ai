import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.notification.send")
def send_notification_background(user_id: str, title: str, message: str):
    """
    Sends in-app notifications/alerts upon background job completion.
    """
    logger.info(f"Background worker sending notification to User {user_id}: {title} - {message}")
    return {"status": "success", "user_id": user_id, "title": title}
