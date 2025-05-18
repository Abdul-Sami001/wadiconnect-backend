from .models import Notification, OrderNotification, UserDevice
from django.db import IntegrityError
import logging
from .fcm_admin import send_push_notification

logger = logging.getLogger(__name__)


def notify_user(user, message, notification_type, payload=None, deduplication_key=None):
    try:
        # 1. Prevent duplicates
        if deduplication_key and Notification.objects.filter(deduplication_key=deduplication_key).exists():
            return

        if not deduplication_key and Notification.objects.filter(
            user=user,
            notification_type=notification_type,
            payload=payload or {}
        ).exists():
            return

        # 2. Create notification in DB
        notification = Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type,
            payload=payload or {},
            deduplication_key=deduplication_key
        )

        # 3. Fetch user devices
        devices = UserDevice.objects.filter(user=user)
        if devices.exists():
            device_tokens = list(devices.values_list('token', flat=True))
            try:
                # 4. Ensure all values in .data are strings
                clean_data = {k: str(v) for k, v in (payload or {}).items()}
                send_push_notification(
                    device_tokens=device_tokens,
                    title="New Notification",
                    body=message,
                    data={
                        "notification_id": str(notification.id),
                        "type": notification_type,
                        **clean_data
                    }
                )
            except Exception as push_error:
                logger.warning(f"Push failed for user {user.id}: {str(push_error)}")
        else:
            logger.info(f"No devices found for user {user.id}")

        return notification

    except IntegrityError as e:
        logger.warning(f"Notification creation failed for user {user.id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in notify_user: {str(e)}")


def notify_sellers(message, notification_type, payload=None):
    from users.models import CustomUser
    sellers = CustomUser.objects.filter(role=CustomUser.SELLER)

    notifications = []
    for seller in sellers:
        if not Notification.objects.filter(
            user=seller,
            notification_type=notification_type,
            payload=payload or {}
        ).exists():
            notifications.append(Notification(
                user=seller,
                message=message,
                notification_type=notification_type,
                payload=payload or {}
            ))
    return Notification.objects.bulk_create(notifications)


def notify_restaurant(seller, message, notification_type, payload=None):
    return notify_user(seller, message, notification_type, payload)


def create_order_notification(order, message, notification_type, snapshot_data=None, original_statuses=None):
    try:
        payload = {
            'order_id': str(order.id),
            'total_amount': str(order.calculate_total_amount()),
            'items_count': str(order.items.count()),
            'vendor_id': str(order.vendor.id) if order.vendor else None
        }

        notification = Notification.objects.create(
            user=order.customer.user,
            message=message,
            notification_type=notification_type,
            payload=payload
        )

        # Ensure status_before is not None if field is NOT nullable
        OrderNotification.objects.update_or_create(
            notification=notification,
            defaults={
                'order': order,
                'status_before': original_statuses.get('delivery_status') if original_statuses else 'unknown',
                'status_after': order.delivery_status,
                'snapshot': snapshot_data or {
                    'items': [
                        {
                            'product': item.product.title,
                            'quantity': item.quantity,
                            'unit_price': str(item.unit_price)
                        } for item in order.items.all()
                    ],
                    'total': str(order.calculate_total_amount()),
                    'delivery_address': order.delivery_address,
                    'payment_status': order.payment_status,
                    'vendor': order.vendor.business_name if order.vendor else None
                }
            }
        )

        return notification

    except Exception as e:
        logger.error(f"Failed to create order notification: {str(e)}")
        return None
