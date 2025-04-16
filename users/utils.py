import random
from django.core.mail import send_mail
from .models import EmailOTP
from django.utils import timezone
from datetime import timedelta

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_to_email(email):
    # Generate OTP and update (or create) the record in EmailOTP table
    otp = generate_otp()
    EmailOTP.objects.update_or_create(email=email, defaults={"otp": otp, "created_at": timezone.now()})
    
    # Send email (using console email backend for development)
    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP code is: {otp}. It is valid for 10 minutes.",
        from_email="noreply@wadiconnect.com",
        recipient_list=[email],
    )

def send_seller_verification_email(email):
    send_mail(
        subject="Seller Profile Verified",
        message="Congratulations! Your seller profile has been verified. You can now access seller features on your account.",
        from_email="noreply@wadiconnect.com",
        recipient_list=[email],
        fail_silently=False,
    )