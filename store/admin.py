from django.contrib import admin
from django.db.models import Avg, Count
from django.utils.html import format_html
from .models import (
    Categories,
    Product,
    ProductImage,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Review,
)
from users.models import CustomerProfile  # Import CustomerProfile


# ====================== PRODUCT ADMIN ======================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ["thumbnail"]

    def thumbnail(self, instance):
        if instance.image:
            return format_html(f'<img src="{instance.image.url}" width="100" />')
        return "-"

    thumbnail.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "vendor",
        "unit_price",
        "inventory_status",
        "average_rating",
        "category",
    ]
    list_editable = ["unit_price"]
    list_per_page = 20
    list_select_related = ["vendor", "category"]
    list_filter = [
        "category",
        ("vendor", admin.RelatedOnlyFieldListFilter),
        "last_update",
    ]
    search_fields = ["title", "description"]
    autocomplete_fields = ["vendor"]  # Now points to SellerProfileAdmin in users app
    inlines = [ProductImageInline]
    actions = ["clear_inventory"]
    readonly_fields = ["last_update"]

    @admin.display(ordering="inventory")
    def inventory_status(self, product):
        return "Low" if product.inventory < 10 else "OK"

    @admin.display(ordering="average_rating")
    def average_rating(self, product):
        result = product.reviews.aggregate(Avg("rating"))["rating__avg"]
        return f"{result:.1f}" if result else "-"

    @admin.action(description="Clear inventory")
    def clear_inventory(self, request, queryset):
        updated = queryset.update(inventory=0)
        self.message_user(request, f"{updated} products inventory cleared")


# ====================== ORDER ADMIN ======================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    min_num = 1
    readonly_fields = ["unit_price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
        "payment_status",
        "delivery_status",
        "placed_at",
        "total_amount",
    ]
    list_editable = ["payment_status", "delivery_status"]
    list_filter = ["payment_status", "delivery_status", "placed_at"]
    autocomplete_fields = ["customer"]  # Now points to CustomerProfileAdmin below
    inlines = [OrderItemInline]
    actions = ["mark_as_completed"]
    date_hierarchy = "placed_at"

    @admin.display(ordering="total_amount")
    def total_amount(self, order):
        return f"${order.calculate_total_amount()}"

    @admin.action(description="Mark selected as completed")
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(payment_status="C", delivery_status="DELIVERED")
        self.message_user(request, f"{updated} orders marked complete")


# ====================== CUSTOMER PROFILE ADMIN ======================
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "phone"]
    search_fields = [
        "user__email",
        "phone",
    ]  # Required for OrderAdmin.autocomplete_fields


# ====================== OTHER ADMIN CLASSES ======================
@admin.register(Categories)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["title", "products_count"]
    search_fields = ["title"]

    @admin.display(ordering="products_count")
    def products_count(self, category):
        return category.products_count

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(products_count=Count("products"))


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "date"]
    list_filter = ["rating", "date"]
    search_fields = ["product__title", "user__email"]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ["product"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "items_count"]
    inlines = [CartItemInline]

    def items_count(self, cart):
        return cart.items.count()


admin.site.register(OrderItem)
admin.site.register(CartItem)
