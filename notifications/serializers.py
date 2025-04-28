from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'notification_type', 'is_read', 'created_at', 'payload']
        read_only_fields = ['id', 'created_at', 'payload']
        
class SuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    deleted = serializers.IntegerField(required=False) 