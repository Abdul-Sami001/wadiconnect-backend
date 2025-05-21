from django.db import models
from django.core.validators import MinValueValidator
from .validators import validate_file_size
from django.conf import settings
from uuid import uuid4
from users.models import CustomerProfile
from django.utils.text import slugify
from django.db.models import Avg 
from notifications.utils import notify_user
from django.contrib.auth import get_user_model


# Create your models here.
class Categories(models.Model):
    title = models.CharField(max_length=255)
   

    def __str__(self) -> str:
        return self.title

    class Meta:
        ordering = ["title"]


class Product(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(null=True, blank=True)
    unit_price = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(1)]
    )
    inventory = models.IntegerField(validators=[MinValueValidator(0)])
    last_update = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(
        Categories, on_delete=models.PROTECT, related_name="products"
    )

    vendor = models.ForeignKey(
        "users.SellerProfile",
        on_delete=models.PROTECT,
        related_name="products",
        
    )  

    def __str__(self) -> str:
        return self.title
    def save(self, *args, **kwargs):
        # Generate slug from title if not present or changed
        if not self.slug or Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            base_slug = slugify(self.title)
            slug = base_slug
            count = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                count += 1
                slug = f"{base_slug}-{count}"
            self.slug = slug
        
        is_update = self.pk is not None
        old_inventory = None

        if is_update:
            old_inventory = Product.objects.get(pk=self.pk).inventory

        super().save(*args, **kwargs)

        if is_update and self.inventory <= 2 and old_inventory > 2:
            if hasattr(self, 'vendor') and self.vendor:
                notify_user(
                    self.vendor.user,
                    f"Low stock: {self.title} ({self.inventory} left).",
                    'low_stock',
                    {'product_id': self.id}
                )
    class Meta:
        ordering = ["title"]


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    # image = models.ImageField(upload_to = r'store\images', validators = [validate_file_size])
    # image = models.URLField(max_length=500)
    image = models.ImageField(upload_to="products/", validators=[validate_file_size])

class Order(models.Model):
    PAYMENT_STATUS_PENDING = "P"
    PAYMENT_STATUS_COMPLETE = "C"
    PAYMENT_STATUS_FAILED = "F"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, "Pending"),
        (PAYMENT_STATUS_COMPLETE, "Complete"),
        (PAYMENT_STATUS_FAILED, "Failed"),
    ]

    DELIVERY_STATUS = (
        ("PREPARING", "Preparing"),
        ("ON_ROUTE", "On Delivery Route"),
        ("DELIVERED", "Delivered"),
    )

    placed_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=1, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING
    )
    customer = models.ForeignKey(CustomerProfile, on_delete=models.PROTECT)
    delivery_status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS, default="PREPARING"
    )
    delivery_address = models.TextField()

    # Add vendor field (required for notifying sellers)
    vendor = models.ForeignKey(
        "users.SellerProfile",
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True
    )
    @property
    def notification_history(self):
        return self.notifications.select_related('notification').order_by('-notification__created_at')
    def get_status_history(self):
        return [
            {
                'status': n.status_after,
                'timestamp': n.notification.created_at,
                'message': n.notification.message
                }
            for n in self.notification_history
    ]

    class Meta:
        permissions = [("cancel_order", "Can cancel order")]

    def calculate_total_amount(self):
        total_amount = sum(
            item.unit_price * item.quantity for item in self.items.all()
        )
        return round(total_amount, 2)

    def save(self, *args, **kwargs):
        created = not self.pk

        if not created:
            old_order = Order.objects.get(pk=self.pk)
            old_delivery_status = old_order.delivery_status
            old_payment_status = old_order.payment_status
        else:
            old_delivery_status = None
            old_payment_status = None

        super().save(*args, **kwargs)

        # 1. Order Confirmation (User + Vendor)
        if created:
            notify_user(
                self.customer.user,
                f"Your order #{self.id} has been confirmed!",
                'order_confirmation',
                {'order_id': self.id}
            )
            if self.vendor:
                notify_user(
                    self.vendor.user,
                    f"New order #{self.id} received!",
                    'new_order',
                    {'order_id': self.id}
                )

        # 2. Delivery Status Changes
        if not created and self.delivery_status != old_delivery_status:
            status_messages = {
                'PREPARING': f"Preparing your order #{self.id}.",
                'ON_ROUTE': f"Your order #{self.id} is on the way!",
                'DELIVERED': f"Your order #{self.id} has been delivered!"
            }
            if self.delivery_status in status_messages:
                notify_user(
                    self.customer.user,
                    status_messages[self.delivery_status],
                    'order_status_change',
                    {'order_id': self.id}
                )

        # 3. Payment Status Changes
        if not created and self.payment_status != old_payment_status:
            if self.payment_status == self.PAYMENT_STATUS_COMPLETE:
                notify_user(
                    self.customer.user,
                    f"Payment of ${self.calculate_total_amount()} for order #{self.id} was successful!",
                    'payment_success',
                    {'order_id': self.id}
                )
                if self.vendor:
                    notify_user(
                        self.vendor.user,
                        f"Payment for order #{self.id} received successfully!",
                        'payment_received',
                        {'order_id': self.id}
                    )
            elif self.payment_status == self.PAYMENT_STATUS_FAILED:
                notify_user(
                    self.customer.user,
                    f"Payment failed for order #{self.id}. Please retry.",
                    'payment_failed',
                    {'order_id': self.id}
                )

    def cancel(self, cancelled_by_user=True):
        self.payment_status = self.PAYMENT_STATUS_FAILED
        self.save()

        notify_user(
            self.customer.user,
            f"Order #{self.id} has been canceled.",
            'order_cancellation',
            {'order_id': self.id}
        )
        if self.vendor:
            notify_user(
                self.vendor.user,
                f"Order #{self.id} was canceled.",
                'restaurant_order_cancellation',
                {'order_id': self.id}
            )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="orderitems"
    )
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="carts"
    )

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        unique_together = [["cart", "product"]]


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    # name = models.CharField(max_length=255) 
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )  # Name of the reviewer
    comment = models.TextField()  # Review content
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True
    )  # Rating out of 5
    date = models.DateField(auto_now_add=True)  # Date when the review was created

    def __str__(self):
        return f"{self.user.email} - {self.rating} Stars"
    def save(self, *args, **kwargs):
     created = not self.pk
     super().save(*args, **kwargs)

    # Send notification when new review created
     if created and self.product.vendor:
        notify_user(
            self.product.vendor.user,
            f"New review from {self.user.email}!",
            'new_review',
            {'review_id': self.id}
        )

     self.update_vendor_rating()

    def delete(self, *args, **kwargs):
        """Update vendor rating on delete"""
        vendor = self.product.vendor
        super().delete(*args, **kwargs)
        self.update_vendor_rating(vendor)

    def update_vendor_rating(self, vendor=None):
        """Recalculate average for all vendor products"""
        vendor = vendor or self.product.vendor
        all_reviews = Review.objects.filter(
            product__vendor=vendor, 
            rating__isnull=False
        )
        avg_rating = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        vendor.average_rating = round(avg_rating, 2)
        vendor.save()

class FavouriteProduct(models.Model):
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="favourite_products"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favourited_by"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.customer.user.email} favourited {self.product.title}"


User = get_user_model()

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.email if self.user else 'Anonymous'}"
