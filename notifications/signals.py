from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from notifications.utils import create_order_notification
from notifications.models import Notification
from users.models import SellerProfile, CustomUser
from store.models import Order
# from django.core.exceptions import ObjectDoesNotExist

# ----------------------------
# 🔹 Seller Verification Signal
# ----------------------------
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
                        notification_type='account',
                        payload={'seller_id': instance.pk}
                    )
        except SellerProfile.DoesNotExist:
            pass

# ----------------------------
# 🔹 User Activation Signal
# ----------------------------
@receiver(post_save, sender=CustomUser)
def handle_user_activation(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_previous_is_active', None) is False and instance.is_active:
        Notification.objects.create(
            user=instance,
            message="Your account has been activated successfully!",
            notification_type='account'
        )

@receiver(pre_save, sender=CustomUser)
def track_user_activation_change(sender, instance, **kwargs):
    try:
        previous = CustomUser.objects.get(pk=instance.pk)
        instance._previous_is_active = previous.is_active
    except CustomUser.DoesNotExist:
        instance._previous_is_active = None

# ----------------------------
# 🔹 Order Tracking Signals
# ----------------------------
@receiver(pre_save, sender=Order)
def track_order_status(sender, instance, **kwargs):
    try:
        original = Order.objects.get(pk=instance.pk)
        instance._original_status = original.delivery_status
    except Order.DoesNotExist:
        instance._original_status = None

@receiver(post_save, sender=Order)
def handle_order_notifications(sender, instance, created, **kwargs):
    if created:
        create_order_notification(
            instance,
            f"New order #{instance.id} placed.",
            'order_status'
        )
        return

    if hasattr(instance, '_original_status') and instance._original_status != instance.delivery_status:
        notification = create_order_notification(
            instance,
            f"Order #{instance.id} status changed: {instance._original_status} → {instance.delivery_status}",
            'order_status'
        )

        # Update the snapshot status fields
        if hasattr(notification, 'order_details'):
            notification.order_details.status_before = instance._original_status
            notification.order_details.status_after = instance.delivery_status
            notification.order_details.save()
