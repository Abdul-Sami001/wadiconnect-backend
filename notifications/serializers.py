from rest_framework import serializers
from .models import Notification
from .models import Notification, OrderNotification
from .models import UserDevice

        
class SuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    deleted = serializers.IntegerField(required=False) 
    
    
class OrderNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderNotification
        fields = ['status_before', 'status_after', 'snapshot']

class NotificationSerializer(serializers.ModelSerializer):
    order_details = OrderNotificationSerializer(read_only=True)
    product_ids = serializers.SerializerMethodField()  # New field

    class Meta:
        model = Notification
        fields = [
            'id', 'message', 'notification_type',
            'is_read', 'created_at', 'payload',
            'order_details', 'product_ids'  # Added product_ids
        ]
        read_only_fields = ['id', 'created_at', 'payload']

    def get_product_ids(self, obj):
        """Extract product IDs from both payload and order snapshot"""
        # First check the notification payload
        if obj.payload and 'product_ids' in obj.payload:
            return obj.payload.get('product_ids', [])
        
        # If not in payload, check order snapshot items
        if hasattr(obj, 'order_details'):
            return [
                str(item.get('product_id')) 
                for item in obj.order_details.snapshot.get('items', [])
                if item.get('product_id')
            ]
        
        return []
class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['token', 'platform']
        extra_kwargs = {
            'platform': {'required': True},
            'token': {'required': True}
        }