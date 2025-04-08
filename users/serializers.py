from rest_framework import serializers
from .models import CustomerProfile, SellerProfile

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['id', 'name', 'phone', 'address', 'created_at', 'updated_at']

class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            'id', 'business_name', 'profile_picture', 'business_address',
         'phone', 'verification_status', 'created_at', 'updated_at'
        ]
