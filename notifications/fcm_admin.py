from firebase_admin import messaging
import logging

logger = logging.getLogger(__name__)

def send_push_notification(device_tokens, title, body, data=None):
    """
    Sends a multicast push via Firebase Admin SDK.
    device_tokens: list of FCM registration tokens (strings)
    """
    if not device_tokens:
        return None

    message = messaging.MulticastMessage(
        tokens=device_tokens,
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data=data or {}
    )

    try:
        response = messaging.send_multicast(message)
        # Clean up invalid tokens
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                error = resp.exception
                logger.warning(f"FCM failed for token {device_tokens[idx]}: {error}")
                from .models import UserDevice
                UserDevice.objects.filter(token=device_tokens[idx]).delete()
        return response
    except Exception as e:
        logger.error(f"Error sending FCM multicast: {e}")
        return None
