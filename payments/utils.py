import hmac
import hashlib
from django.conf import settings
from django.http import HttpResponseForbidden

def verify_fastpay_signature(payload, received_signature):
    """
    Verify FastPay callback signature using HMAC-SHA256
    """
    secured_key = settings.FASTPAY_SECURED_KEY.encode()
    expected_signature = hmac.new(
        secured_key,
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)