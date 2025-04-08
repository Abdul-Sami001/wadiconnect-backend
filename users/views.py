from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import CustomerProfile, SellerProfile
from .serializers import CustomerProfileSerializer, SellerProfileSerializer

class CustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Ensure the logged-in user is a customer
        if self.request.user.role != 'customer':
            raise PermissionDenied("You do not have access to this resource.")
        return self.request.user.customer_profile


class SellerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Ensure the logged-in user is a seller
        if self.request.user.role != 'seller':
            raise PermissionDenied("You do not have access to this resource.")
        return self.request.user.seller_profile
