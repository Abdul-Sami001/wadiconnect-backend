from .models import Notification, OrderNotification, UserDevice
from django.db import IntegrityError
import logging
from .fcm_admin import send_push_notification

logger = logging.getLogger(__name__)
def get_notification_content(notification_type, context):
    order_id = context.get('order_id', '')
    vendor = context.get('vendor', '')
    
    titles = {
        'order_confirmation': f"Order #{order_id} Confirmed!",
        'order_status_change': f"Order #{order_id} Updated",
        'delivery_delay': f"Order #{order_id} Delayed",
        'order_cancellation': f"Order #{order_id} Cancelled",
        'payment_success': f"Payment Successful",
        'payment_failed': f"Payment Failed",
        'review_reminder': "Leave a Review",
        'new_order': f"New Order Received - #{order_id}",
        'restaurant_order_cancellation': f"Order #{order_id} Cancelled by Customer",
        'payment_received': "Payment Received",
        'account': "Account Update",
    }

    bodies = {
        'order_confirmation': "Your order has been confirmed. Sit tight, it's being prepared!",
        'order_status_change': f"Your order #{order_id} has been updated. Check the latest status.",
        'delivery_delay': f"Sorry! Order #{order_id} will be late. Thanks for your patience.",
        'order_cancellation': f"Your order #{order_id} was cancelled.",
        'payment_success': f"We received your payment for Order #{order_id}.",
        'payment_failed': f"There was an issue processing payment for Order #{order_id}.",
        'review_reminder': "Tell us how your order went. Your feedback helps us improve.",
        'new_order': f"You have received a new order #{order_id}. Please confirm it ASAP.",
        'restaurant_order_cancellation': f"Customer has cancelled Order #{order_id}.",
        'payment_received': f"You’ve received payment for Order #{order_id}.",
        'account': "Your account has been updated or verified successfully.",
    }

    return titles.get(notification_type, "New Notification"), bodies.get(notification_type, "You have a new update.")


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
                title, body = get_notification_content(notification_type, payload or {})

                send_push_notification(
                    device_tokens=device_tokens,
                    title = title,
                    body=body,
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
    
    existing = Notification.objects.filter(
        user__in=sellers,
        notification_type=notification_type,
        payload=payload or {}
    ).values_list('user_id', flat=True)

    new_notifications = [
        Notification(
            user=seller,
            message=message,
            notification_type=notification_type,
            payload=payload or {}
        ) for seller in sellers if seller.id not in existing
    ]
    return Notification.objects.bulk_create(new_notifications, ignore_conflicts=True)


def notify_restaurant(seller, message, notification_type, payload=None):
    return notify_user(seller, message, notification_type, payload)


def create_order_notification(order, message, notification_type, snapshot_data=None, original_statuses=None):
    try:
        product_ids = [str(item.product.id) for item in order.items.all()] 
        payload = {
            'order_id': str(order.id),
            'total_amount': str(order.calculate_total_amount()),
            'items_count': str(order.items.count()),
            'vendor_id': str(order.vendor.id) if order.vendor else None,
            'product_ids': product_ids
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
                'status_before': original_statuses.get('delivery_status') if original_statuses else None,
                'status_after': order.delivery_status,
                'snapshot': snapshot_data or {
                    'items': [
                        {
                            'product': item.product.title,
                            'product_id': str(item.product.id), 
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
