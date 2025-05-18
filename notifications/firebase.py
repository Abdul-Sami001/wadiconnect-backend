import os
import firebase_admin
from firebase_admin import credentials
import logging
logger = logging.getLogger(__name__)

# BASE_DIR = <project root> (same as in your settings.py)
from django.conf import settings

SERVICE_ACCOUNT_PATH = os.path.join(settings.BASE_DIR, "Push-notifications-key.json")

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
except Exception as e:
    logger.error(f"Firebase initialization failed: {str(e)}")
