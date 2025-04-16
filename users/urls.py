from django.urls import path
from .views import RegisterUserView, VerifyOTPView, ResendOTPView, UpgradeToSellerView, ProfileView


urlpatterns = [
    path("register/", RegisterUserView.as_view(), name="register"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("upgrade-seller/", UpgradeToSellerView.as_view(), name="upgrade-seller"),
    path("profile/", ProfileView.as_view(), name="profile"),
]