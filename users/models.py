from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import random
from datetime import timedelta
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    
    def create_user(self, email, password=None, **extra_fields):
        print("Extra fields ", extra_fields, self, email)
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        # Create a user without a username field
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    CUSTOMER = "customer"
    SELLER = "seller"

    ROLE_CHOICES = [
        (CUSTOMER, "Customer"),
        (SELLER, "Seller"),
    ]

    username = None  # Remove the default username field
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)
    is_active = models.BooleanField(
        default=False
    )  # Inactive until activation (e.g., OTP verified)
    otp = models.CharField(max_length=6, blank=True, null=True)  # OTP field

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # Assign our custom manager

    def __str__(self):
        return self.email


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        
    )
    # name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    name    = models.CharField(max_length=100, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_picture = models.ImageField(
    upload_to='profile_pictures/customers/', blank=True, null=True
        )

    def __str__(self):
        return self.user.email


class SellerProfile(models.Model):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

    VERIFICATION_STATUS_CHOICES = [
        (PENDING, "Pending"),
        (VERIFIED, "Verified"),
        (REJECTED, "Rejected"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_profile",
    )
    business_name = models.CharField(max_length=100,)
    business_description = models.TextField(blank=True, null=True)
    opening_closing_time = models.CharField(max_length=255, blank=True, null=True)  # E.g. "9 AM - 5 PM"
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True
    )
    business_address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=15)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS_CHOICES, default=PENDING
    )
    # //new l
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} ({self.user.email})"


class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() <= self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - OTP: {self.otp}"