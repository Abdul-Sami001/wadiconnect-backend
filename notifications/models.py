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
        ('order_status', 'Order Status'),
        ('promotion', 'Promotion'),
        ('account', 'Account'),
        ('inventory', 'Inventory'),
        ('review', 'Review'),
        ('support', 'Support'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
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
