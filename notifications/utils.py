from .models import Notification

from .models import Notification, OrderNotification

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
    
def notify_restaurant(seller, message, notification_type, payload=None):
    return Notification.objects.create(
        user=seller,
        message=message,
        notification_type=notification_type,
        payload=payload or {}
    )
def create_order_notification(order, message, notification_type):
    from store.models import Order
    notification = Notification.objects.create(
        user=order.customer.user,
        message=message,
        notification_type=notification_type,
        payload={
            'order_id': order.id,
            'total_amount': str(order.calculate_total_amount()),
            'items_count': order.items.count()
        }
    )

    OrderNotification.objects.create(
        notification=notification,
        order=order,
        status_before=order.delivery_status,
        status_after=order.delivery_status,
        snapshot={
            'items': [
                {
                    'product': item.product.title,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price)
                } for item in order.items.all()
            ],
            'total': str(order.calculate_total_amount()),
            'delivery_address': order.delivery_address,
            'payment_status': order.payment_status
        }
    )
    return notification