import requests
import json
import os
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from django.conf import settings

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_PATH = os.path.join(settings.BASE_DIR, "Push-notifications-key.json")
PROJECT_ID = "kwick-6315e"  # You can also use settings.FIREBASE_PROJECT_ID if set

def send_push_notification(device_tokens, title, body, data=None):
    try:
        # Authenticate using service account
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_PATH,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        credentials.refresh(Request())
        access_token = credentials.token

        # Convert all payload data values to strings
        data = {k: str(v) for k, v in (data or {}).items()}

        # Firebase endpoint and headers
        url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        for token in device_tokens:
            message = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "data": data
                }
            }

            response = requests.post(url, headers=headers, json=message)

            if response.status_code == 200:
                logger.info(f"Push sent to {token}")
            else:
                logger.warning(f"Failed to send push to {token}: {response.status_code} - {response.text}")
                
                try:
                    # Parse error from FCM response
                    error_status = response.json().get("error", {}).get("status", "").upper()
                    if error_status in ["UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"]:
                        from .models import UserDevice
                        UserDevice.objects.filter(token=token).delete()
                        logger.info(f"Deleted invalid token: {token}")
                except Exception as parse_err:
                    logger.warning(f"Could not parse FCM response JSON: {parse_err}")

    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}")
