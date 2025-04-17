import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from .models import FastPayTransaction
from .services import FastPayService
from .utils import verify_fastpay_signature

logger = logging.getLogger(__name__)

@csrf_exempt
def initiate_payment(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    
    try:
        # Validate input data
        data = json.loads(request.body)
        required_fields = ['amount', 'customer_name', 'customer_email', 'customer_phone']
        if not all(field in data for field in required_fields):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Create transaction
        transaction = FastPayTransaction.objects.create(
            user=request.user if request.user.is_authenticated else None,
            transaction_id=str(uuid.uuid4()),
            amount=data['amount'],
            customer_name=data['customer_name'],
            customer_email=data['customer_email'],
            customer_phone=data['customer_phone'],
            currency=data.get('currency', 'BDT')
        )

        # Prepare payment data
        payment_data = {
            'amount': transaction.amount,
            'customer_phone': transaction.customer_phone,
            'customer_email': transaction.customer_email,
            'transaction_id': transaction.transaction_id,
            'customer_ip': request.META.get('REMOTE_ADDR', '127.0.0.1')
        }

        # Initiate payment
        response = FastPayService.initiate_payment(payment_data)
        if not response:
            transaction.status = 'failed'
            transaction.save()
            return JsonResponse({'error': 'Payment gateway error'}, status=500)

        return JsonResponse(response)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def payment_callback(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    
    try:
        # Verify signature
        signature = request.headers.get('X-FastPay-Signature')
        if not verify_fastpay_signature(request.body, signature):
            return HttpResponseForbidden("Invalid signature")

        data = json.loads(request.body)
        transaction_id = data.get('order_id')
        status = data.get('status', '').lower()

        transaction = FastPayTransaction.objects.get(transaction_id=transaction_id)
        transaction.status = status
        transaction.save()

        return JsonResponse({'status': 'success'})

    except FastPayTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)