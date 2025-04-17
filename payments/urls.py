from django.urls import path
from .views import initiate_payment, payment_callback

urlpatterns = [
    path('initiate-payment/', initiate_payment, name='initiate-payment'),
    path('payment-callback/', payment_callback, name='payment-callback'),
]