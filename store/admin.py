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
    Feedback
)
from users.models import CustomerProfile


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
    search_fields = ["title", "description"]         # for Product autocomplete, etc.
    autocomplete_fields = ["vendor"]
    inlines = [ProductImageInline]
    actions = ["clear_inventory"]
    readonly_fields = ["last_update"]

    fieldsets = (
        ("Product Information", {
            "fields": ("title", "description", "category", "vendor", "unit_price", "inventory")
        }),
        ("System Info", {
            "fields": ("last_update",)
        }),
    )

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
    readonly_fields = ["unit_price", "product_thumbnail"]

    def product_thumbnail(self, instance):
        if instance.product and instance.product.productimage_set.exists():
            return format_html(
                '<img src="{}" width="50" />',
                instance.product.productimage_set.first().image.url
            )
        return "-"
    product_thumbnail.short_description = "Product Image"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
         "payment_status",    # <-- raw field, will render as dropdown
        "delivery_status",   # <-- raw field, will render as dropdown
        "placed_at",
        "total_amount",
    ]
    
     # Allow inline editing of those two fields:
    list_editable = ["payment_status", "delivery_status"]
    # Make only ID and customer clickable to open the detail page:
    list_display_links = ["id", "customer"]
    search_fields = [
        "id",
        "customer__user__email",
        "customer__name",
        "customer__phone"
    ]                                                # fixes autocomplete on customer
    list_filter = ["payment_status", "delivery_status", "placed_at"]
    autocomplete_fields = ["customer"]
    inlines = [OrderItemInline]
    actions = ["mark_as_completed"]
    date_hierarchy = "placed_at"
    readonly_fields = ["placed_at"]

    fieldsets = (
        ("Customer Information", {
            "fields": ("customer",)
        }),
        ("Order Status", {
            "fields": ("payment_status", "delivery_status")
        }),
        ("Timestamps", {
            "fields": ("placed_at",)
        }),
    )

    @admin.display(description="Payment Status")
    def colored_payment_status(self, obj):
        color = "green" if obj.payment_status == "C" else "red"
        return format_html('<b style="color:{};">{}</b>', color, obj.get_payment_status_display())

    @admin.display(description="Delivery Status")
    def colored_delivery_status(self, obj):
        color = "green" if obj.delivery_status == "DELIVERED" else "orange"
        return format_html('<b style="color:{};">{}</b>', color, obj.get_delivery_status_display())

    @admin.display(ordering="total_amount")
    def total_amount(self, order):
        return f"Rs.{order.calculate_total_amount()}"

    @admin.action(description="Mark selected as completed")
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(payment_status="C", delivery_status="DELIVERED")
        self.message_user(request, f"{updated} orders marked complete")

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, OrderItem) and not instance.unit_price:
                instance.unit_price = instance.product.unit_price
            instance.save()
        formset.save_m2m()


# ====================== CUSTOMER PROFILE ADMIN ======================
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "phone"]
    search_fields = ["user__email", "name", "phone"]  # needed for autocomplete
    autocomplete_fields = ["user"]


# ====================== CATEGORY ADMIN ======================
@admin.register(Categories)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["title", "products_count"]
    search_fields = ["title"]

    @admin.display(ordering="products_count")
    def products_count(self, category):
        return category.products_count

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(products_count=Count("products"))


# ====================== REVIEW ADMIN ======================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "date"]
    list_filter = ["rating", "date"]
    search_fields = ["product__title", "user__email"]  # needed for product & user autocompletes
    autocomplete_fields = ["product", "user"]


# ====================== CART ADMIN ======================
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ["product"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "items_count"]
    search_fields = ["id"]               # needed for CartItemInline.autocomplete_fields
    readonly_fields = ["created_at"]
    inlines = [CartItemInline]

    def items_count(self, cart):
        return cart.items.count()


# ====================== ORDER ITEM & CART ITEM ADMIN ======================
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "unit_price"]
    search_fields = ["order__id", "product__title"]  # needed for autocompletes
    autocomplete_fields = ["order", "product"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity"]
    search_fields = ["cart__id", "product__title"]  # needed for autocompletes
    autocomplete_fields = ["cart", "product"]


# ====================== FEEDBACK ADMIN ======================
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("message", "user__email")  # needed for user autocomplete
    autocomplete_fields = ["user"]
