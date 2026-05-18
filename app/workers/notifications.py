from app.core.celery_app import celery_app
import firebase_admin
from firebase_admin import messaging, credentials
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase
if settings.FCM_CREDENTIAL_PATH:
    try:
        cred = credentials.Certificate(settings.FCM_CREDENTIAL_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")

@celery_app.task
def send_push_notification(user_id: str, title: str, body: str, data: dict = None):
    """
    Sends a push notification using Firebase Cloud Messaging.
    """
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Skipping push notification.")
        return
        
    # In a real application, you would look up the user's FCM tokens from the database here
    # Example:
    # tokens = get_user_fcm_tokens(user_id)
    tokens = ["dummy_token_123"] # Replace with DB lookup
    
    if not tokens:
        return
        
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )
    
    try:
        response = messaging.send_multicast(message)
        logger.info(f"Successfully sent message to {response.success_count} devices")
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
