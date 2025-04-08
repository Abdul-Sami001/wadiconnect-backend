from django.urls import path
from .views import CustomerProfileView, SellerProfileView

urlpatterns = [
    path('customers/profile/', CustomerProfileView.as_view(), name='customer-profile'),
    path('sellers/profile/', SellerProfileView.as_view(), name='seller-profile'),
]
