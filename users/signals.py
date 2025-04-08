from django.db.models.signals import post_save
from django.dispatch import receiver

from wadiconnect import settings
from .models import CustomUser, CustomerProfile, SellerProfile
from django.core.mail import EmailMessage
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create profiles based on the user's role.
    """
    if created:
        if instance.role == CustomUser.CUSTOMER:
            CustomerProfile.objects.create(user=instance)
        elif instance.role == CustomUser.SELLER:
            SellerProfile.objects.create(user=instance)



@receiver(post_save, sender=SellerProfile)
def update_user_role_on_verification(sender, instance, **kwargs):
    """
    Automatically update the user's role to 'seller' when the seller profile is verified.
    """
    if instance.verification_status == 'verified' and instance.user.role != 'seller':
        instance.user.role = 'seller'
        instance.user.save()

        email = EmailMessage(
            subject="Your Seller Profile Has Been Verified",
            body=f"<p>Dear {instance.business_name},</p>"
                 "<p>Congratulations! Your seller profile on <b>WadiConnect</b> has been verified. "
                 "You can now access seller features and start listing your products.</p>"
                 "<p>Thank you for joining us!</p>"
                 "<p><b>WadiConnect Team</b></p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.user.email],
        )
        email.content_subtype = "html"  # Set email content type to HTML
        email.send()