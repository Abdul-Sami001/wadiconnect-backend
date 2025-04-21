# store/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Review

@receiver([post_save, post_delete], sender=Review)
def handle_review_changes(sender, instance, **kwargs):
    instance.update_vendor_rating()