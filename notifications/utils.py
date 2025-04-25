from .models import Notification

def notify_user(user, message, notification_type, payload=None):
    return Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type,
        payload=payload or {}
    )

def notify_sellers(message, notification_type, payload=None):
    from users.models import CustomUser
    sellers = CustomUser.objects.filter(role=CustomUser.SELLER)
    return Notification.objects.bulk_create([
        Notification(
            user=seller,
            message=message,
            notification_type=notification_type,
            payload=payload or {}
        ) for seller in sellers
    ])