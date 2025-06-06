from django.contrib import admin
from .models import CustomerProfile, SellerProfile, CustomUser
from .utils import send_seller_verification_email  # function we define in utils.py
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
# admin.site.register(CustomerProfile)
@admin.register(CustomUser)
class CustomUserAdmin(DefaultUserAdmin):
    model = CustomUser
    list_display = ("email", "role", "is_staff", "is_active")
    list_filter  = ("role", "is_staff", "is_active")
    search_fields = ("email",)                # ← this is the critical bit
    ordering      = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "is_active", "is_staff"),
        }),
    )

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "business_name", "verification_status", "created_at")
    list_filter = ("verification_status",)
    search_fields = ["user__email", "business_name"]
    actions = ["mark_as_verified"]

    def mark_as_verified(self, request, queryset):
        queryset.update(verification_status="verified")

    mark_as_verified.short_description = "Mark selected profiles as Verified"

    def save_model(self, request, obj, form, change):
        # Check if verification_status changed and is now VERIFIED
        if change:
            old_obj = SellerProfile.objects.get(pk=obj.pk)
            if old_obj.verification_status != obj.verification_status and obj.verification_status == 'verified':
                send_seller_verification_email(obj.user.email)
        super().save_model(request, obj, form, change)
    