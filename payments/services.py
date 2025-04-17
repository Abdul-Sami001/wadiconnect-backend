import requests
import logging
from django.conf import settings
from uuid import uuid4
from django.utils import timezone

logger = logging.getLogger(__name__)

class FastPayService:
    @staticmethod
    def get_auth_token():
        """Retrieve FastPay authentication token"""
        try:
            response = requests.post(
                f"{settings.FASTPAY_BASE_URL}/token",
                data={
                    'merchant_id': settings.FASTPAY_MERCHANT_ID,
                    'secured_key': settings.FASTPAY_SECURED_KEY,
                    'grant_type': 'client_credentials'
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('token')
        except requests.exceptions.RequestException as e:
            logger.error(f"FastPay token error: {str(e)}")
            return None

    @staticmethod
    def initiate_payment(transaction_data):
        """Initiate payment with FastPay"""
        try:
            token = FastPayService.get_auth_token()
            if not token:
                return None

            payload = {
                'basket_id': str(uuid4()),
                'txnamt': str(transaction_data['amount']),
                'order_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                'customer_mobile_no': transaction_data['customer_phone'],
                'customer_email_address': transaction_data['customer_email'],
                'account_type_id': '3',  # Default account type
                'bank_code': transaction_data.get('bank_code', ''),
                'transaction_id': transaction_data['transaction_id'],
                'customer_ip': transaction_data.get('customer_ip', '127.0.0.1'),
                'otp_required': 'no',
                'recurring_txn': 'no'
            }

            response = requests.post(
                f"{settings.FASTPAY_BASE_URL}/transaction",
                data=payload,
                headers={
                    'Authorization': f"Bearer {token}",
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Payment initiation error: {str(e)}")
            return None