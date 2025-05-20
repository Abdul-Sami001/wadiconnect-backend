
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from notifications.utils import create_order_notification, notify_user  # ✅ Add notify_user
from notifications.models import Notification
from users.models import SellerProfile, CustomUser
from store.models import Order

# 🔹 Seller Verification
@receiver(post_save, sender=SellerProfile)
def handle_seller_verification(sender, instance, created, **kwargs):
    if not created:
        try:
            old = SellerProfile.objects.get(pk=instance.pk)
            if old.verification_status != instance.verification_status:
                message = {
                    SellerProfile.VERIFIED: "Your seller account has been verified!",
                    SellerProfile.REJECTED: "Your seller verification was rejected. Please check your details."
                }.get(instance.verification_status)

                if message:
                    Notification.objects.create(
                        user=instance.user,
                        message=message,
                        notification_type='account',  # ✅ Make sure this exists in TYPE_CHOICES
                        payload={'seller_id': instance.pk}
                    )
        except SellerProfile.DoesNotExist:
            pass

# 🔹 Track user activation
@receiver(pre_save, sender=CustomUser)
def track_user_activation_change(sender, instance, **kwargs):
    try:
        previous = CustomUser.objects.get(pk=instance.pk)
        instance._previous_is_active = previous.is_active
    except CustomUser.DoesNotExist:
        instance._previous_is_active = None

@receiver(post_save, sender=CustomUser)
def handle_user_activation(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_previous_is_active', None) is False and instance.is_active:
        Notification.objects.create(
            user=instance,
            message="Your account has been activated successfully!",
            notification_type='account'  # ✅ Ensure it's in TYPE_CHOICES
        )

# 🔹 Track order changes
@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    try:
        original = Order.objects.get(pk=instance.pk)
        instance._original_data = {
            'delivery_status': original.delivery_status if original else None,
            'payment_status': original.payment_status if original else None,
            'is_cancelled': original.payment_status == Order.PAYMENT_STATUS_FAILED
        }

        instance._snapshot_data = {
            'items': [
                {
                    'product': item.product.title,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price)
                } for item in instance.items.all()
            ],
            'total': str(instance.calculate_total_amount()),
            'delivery_address': instance.delivery_address,
            'payment_status': instance.payment_status,
            'vendor': instance.vendor.business_name if instance.vendor else None
        }

    except Order.DoesNotExist:
        instance._original_data = {
            'delivery_status': None,
            'payment_status': None,
            'is_cancelled': False
        }
        instance._snapshot_data = {}

# 🔹 Handle order notifications
@receiver(post_save, sender=Order)
def handle_order_notifications(sender, instance, created, **kwargs):
    try:
        original = instance._original_data
        snapshot = instance._snapshot_data

        # Create main notification snapshot
        notification = create_order_notification(
            instance,
            f"Order #{instance.id} update",
            'order_status',
            snapshot_data=snapshot,
            original_statuses=original
        )

        # 1. New Order
        if created:
            notification.message = f"New order #{instance.id} placed"
            notification.notification_type = 'new_order'
            notification.save()

            notify_user(
                instance.customer.user,
                f"Order #{instance.id} confirmed!",
                'order_confirmation',
                {'order_id': instance.id}
            )

        # 2. Delivery Status Change
        if instance.delivery_status != original['delivery_status']:
            notification.message = (
                f"Order #{instance.id} status changed: "
                f"{original['delivery_status']} → {instance.delivery_status}"
            )
            notification.save()

        # 3. Payment Status Change
        if instance.payment_status != original['payment_status']:
            msg_type, message = {
                Order.PAYMENT_STATUS_COMPLETE: (
                    'payment_success',
                    f"Payment for order #{instance.id} received"
                ),
                Order.PAYMENT_STATUS_FAILED: (
                    'payment_failed',
                    f"Payment failed for order #{instance.id}"
                )
            }.get(instance.payment_status, (None, None))

            if message:
                notify_user(
                    instance.customer.user,
                    message,
                    msg_type,
                    {'order_id': instance.id}
                )
                if instance.vendor:
                    notify_user(
                        instance.vendor.user,
                        message,
                        'payment_received' if msg_type == 'payment_success' else 'restaurant_order_cancellation',
                        {'order_id': instance.id}
                    )

        # 4. Cancellation
        if (original['payment_status'] != Order.PAYMENT_STATUS_FAILED and
            instance.payment_status == Order.PAYMENT_STATUS_FAILED):
            notification.message = f"Order #{instance.id} cancelled"
            notification.notification_type = 'order_cancellation'
            notification.save()

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Notification signal error for order {instance.id}: {str(e)}")