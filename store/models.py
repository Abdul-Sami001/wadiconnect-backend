from django.db import models
from django.core.validators import MinValueValidator
from .validators import validate_file_size
from django.conf import settings
from uuid import uuid4
from users.models import CustomerProfile
from django.utils.text import slugify
from django.db.models import Avg 



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
        null=True,
        blank=True,
    )  # Remove null and blank

    def __str__(self) -> str:
        return self.title

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

    placed_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=1, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING
    )
    customer = models.ForeignKey(CustomerProfile, on_delete=models.PROTECT)
    DELIVERY_STATUS = (
        ("PREPARING", "Preparing"),
        ("ON_ROUTE", "On Delivery Route"),
        ("DELIVERED", "Delivered"),
    )
    delivery_status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS, default="PREPARING"
    )
    delivery_address = models.TextField()  # Snapshot at order time
    class Meta:
        permissions = [("cancel_order", "Can cancel order")]

    def calculate_total_amount(self):
        total_amount = sum(
            item.unit_price * item.quantity for item in self.items.all()
        )  # Calculate total from OrderItems
        # total_amount *= Decimal("0.9")
        return round(total_amount, 2)


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
        """Update vendor rating on save"""
        super().save(*args, **kwargs)
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
