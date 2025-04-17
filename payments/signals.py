from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FastPayTransaction
from django.core.mail import send_mail

@receiver(post_save, sender=FastPayTransaction)
def handle_payment_status(sender, instance, **kwargs):
    """
    Send notifications on payment status changes
    """
    if instance.status_changed():
        subject = f"Payment {instance.status.upper()} - {instance.transaction_id}"
        message = f"Your payment of {instance.amount} {instance.currency} is {instance.status}"
        
        send_mail(
            subject,
            message,
            'noreply@yourdomain.com',
            [instance.customer_email],
            fail_silently=True
        )