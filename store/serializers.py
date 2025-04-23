from rest_framework import serializers
from uuid import UUID
from .models import (
    Categories,
    Product,
    ProductImage,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Review,
    FavouriteProduct,
)
from users.models import SellerProfile
from django.db.models import Avg

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ["id", "title"]
        read_only_fields = ["id"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "product"]
        read_only_fields = ["id"]
        extra_kwargs = {"product": {"write_only": True}}

    def to_representation(self, instance):
        """Add full image URL in API response"""
        representation = super().to_representation(instance)
        request = self.context.get("request")
        if request and instance.image:
            representation["image"] = request.build_absolute_uri(instance.image.url)
        return representation


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=SellerProfile.objects.all(), default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "unit_price",
            "inventory",
            "category",
            "vendor",
            "images",
            "last_update",
        ]
        read_only_fields = ["id", "slug", "last_update"]
        extra_kwargs = {"category": {"required": True}}

    def validate_vendor(self, value):
        """Ensure vendor is verified"""
        if not value.verification_status == "verified":
            raise serializers.ValidationError("Only verified sellers can add products")
        return value


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "product", "comment", "rating", "date"]
        read_only_fields = ["id", "user", "date"]
        extra_kwargs = {"product": {"write_only": True}}

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1-5")
        return value

    def create(self, validated_data):
        """Auto-set the user from request"""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

class CreateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['delivery_address']

    def create(self, validated_data):
        # Automatically set the customer from the request's user
        request = self.context.get('request')
        if request and hasattr(request.user, 'customer_profile'):
            validated_data['customer'] = request.user.customer_profile
            return super().create(validated_data)
        else:
            raise serializers.ValidationError("Customer profile not found.")
class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    unit_price = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_title", "quantity", "unit_price"]
        read_only_fields = ["id", "unit_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer_email = serializers.EmailField(
        source="customer.user.email", read_only=True
    )
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "placed_at",
            "payment_status",
            "delivery_status",
            "delivery_address",
            "customer",
            "customer_email",
            "items",
            "total",
        ]
        read_only_fields = ["id", "placed_at", "total"]

    def get_total(self, obj):
        return obj.calculate_total_amount()

    def create(self, validated_data):
        """Handle nested order items creation"""
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data["product"],
                quantity=item_data["quantity"],
                unit_price=item_data["product"].unit_price,
            )
        return order


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total_price']
        read_only_fields = ['id', 'product', 'total_price']

    def get_total_price(self, obj):
        return obj.quantity * obj.product.unit_price

    def create(self, validated_data):
        cart_id = self.context.get('cart_id')
        if not cart_id:
            raise serializers.ValidationError("Cart ID is required")

        return CartItem.objects.create(
            cart_id=cart_id,
            product_id=validated_data['product_id'],
            quantity=validated_data['quantity']
        )
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    # Optional: Display who owns the cart (for admins maybe)
    customer = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Cart
        fields = ["id", "created_at", "items", "total", "customer"]
        read_only_fields = ["id", "created_at", "total"]

    def get_total(self, obj):
        return sum(item.quantity * item.product.unit_price for item in obj.items.all())

class SellerProductSerializer(serializers.ModelSerializer):
    """Variant for seller dashboard with extended fields"""

    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ["review_count", "average_rating"]

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(Avg("rating"))["rating__avg"]


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """For partial updates to order status"""

    class Meta:
        model = Order
        fields = ["payment_status", "delivery_status"]
        extra_kwargs = {
            "payment_status": {"required": False},
            "delivery_status": {"required": False},
        }


class FavouriteProductSerializer(serializers.ModelSerializer):
    product_title = serializers.ReadOnlyField(source="product.title")

    class Meta:
        model = FavouriteProduct
        fields = ["id", "product", "product_title", "added_at"]