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

    class Meta:
        model = Notification
        fields = [
            'id', 'message', 'notification_type',
            'is_read', 'created_at', 'payload',
            'order_details'
        ]
        read_only_fields = ['id', 'created_at', 'payload']
class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['token', 'platform']

