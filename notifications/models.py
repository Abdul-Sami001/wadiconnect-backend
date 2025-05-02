from django.db import models
from django.conf import settings
from django.utils import timezone

class NotificationManager(models.Manager):
    def unread(self):
        return self.filter(is_read=False)

    def mark_all_as_read(self, user):
        return self.filter(user=user, is_read=False).update(is_read=True)
class Notification(models.Model):
    TYPE_CHOICES = [
        # User-facing
        ('order_confirmation', 'Order Confirmation'),
        ('order_status_change', 'Order Status Change'),
        ('delivery_delay', 'Delivery Delay'),
        ('order_cancellation', 'Order Cancellation'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('refund_processed', 'Refund Processed'),
        ('discount_offer', 'Discount/Coupon Offer'),
        ('new_restaurant', 'New Restaurant Alert'),
        ('review_reminder', 'Review Reminder'),
        ('restaurant_reply', 'Restaurant Reply'),
        # Restaurant-facing
        ('new_order', 'New Order Received'),
        ('restaurant_order_cancellation', 'Order Cancellation (Restaurant)'),
        ('new_review', 'New Review Posted'),
        ('low_stock', 'Low Stock Alert'),
        ('payment_received', 'Payment Received'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(blank=True, null=True)

    # ✅ Apply your custom manager here
    objects = NotificationManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: {self.message[:50]}"

    def mark_as_read(self):
        self.is_read = True
        self.save()
class OrderNotification(models.Model):
    notification = models.OneToOneField(
        Notification, 
        on_delete=models.CASCADE,
        related_name='order_details'
    )
    order = models.ForeignKey(
        'store.Order', 
        on_delete=models.PROTECT,
        related_name='notifications'
    )
    status_before = models.CharField(max_length=20)
    status_after = models.CharField(max_length=20)
    snapshot = models.JSONField()

    class Meta:
         indexes = [
        models.Index(fields=['order']),  # Valid field on OrderNotification
    ]
         