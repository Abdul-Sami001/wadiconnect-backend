
from django.contrib import admin
from .models import CustomerProfile, SellerProfile, CustomUser

admin.site.register(CustomerProfile)
admin.site.register(CustomUser)

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'verification_status', 'created_at')
    list_filter = ('verification_status',)
    actions = ['mark_as_verified']

    def mark_as_verified(self, request, queryset):
        queryset.update(verification_status='verified')
    mark_as_verified.short_description = "Mark selected profiles as Verified"

