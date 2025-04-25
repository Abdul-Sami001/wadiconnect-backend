from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import SellerProfile, CustomUser
from .models import Notification

@receiver(post_save, sender=SellerProfile)
def handle_seller_verification(sender, instance, **kwargs):
    if not kwargs['created']:
        try:
            old = SellerProfile.objects.get(pk=instance.pk)
            if old.verification_status != instance.verification_status:
                message = {
                    SellerProfile.VERIFIED: "Your seller account has been verified!",
                    SellerProfile.REJECTED: "Seller verification rejected. Please check your details."
                }.get(instance.verification_status)
                
                if message:
                    Notification.objects.create(
                        user=instance.user,
                        message=message,
                        notification_type='account'
                    )
        except SellerProfile.DoesNotExist:
            pass

@receiver(post_save, sender=CustomUser)
def handle_user_activation(sender, instance, **kwargs):
    if not kwargs['created'] and instance.tracker.has_changed('is_active') and instance.is_active:
        Notification.objects.create(
            user=instance,
            message="Account activated successfully!",
            notification_type='account'
        )