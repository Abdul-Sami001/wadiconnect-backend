from datetime import datetime
from django.forms import ValidationError
from rest_framework import serializers
from uuid import UUID
from .models import (
    Categories,
    Deal,
    Product,
    ProductImage,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Review,
    FavouriteProduct,
    Feedback,
)
from users.models import SellerProfile
from django.db.models import Avg
from django.utils.dateparse import parse_datetime
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


class ProductCreateSerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=SellerProfile.objects.all(),
        required=False  # You'll set this manually
    )
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    class Meta:
        model = Product
        fields = [
            "id", "title", "description", "unit_price",
            "inventory", "category", "images", "vendor"
        ]
        read_only_fields = ["id", "vendor"]
        
    def create(self, validated_data):
        images = validated_data.pop("images", [])
        product = Product.objects.create(**validated_data)

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        return product

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=SellerProfile.objects.all(),
        required=False  # We'll set this in perform_create
    )
    vendor_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.title", read_only=True)
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
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
            "category_name",
            "vendor",
            "vendor_name",
            "images",
            "last_update",
            "review_count",
            "average_rating",
        ]
        read_only_fields = ["id", "slug", "last_update", "category_name", "vendor_name", "review_count", "average_rating",]
        extra_kwargs = {"category": {"required": True}}

    
    def get_vendor_name(self, obj):
        return obj.vendor.business_name if obj.vendor and obj.vendor.business_name else None

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg is not None else 0
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product_name = serializers.CharField(source='product.title', read_only=True)
    product_image = serializers.SerializerMethodField()
    class Meta:
        model = Review
        fields = ["id", "user", "product","product_name", "product_image", "comment", "rating", "date"]
        read_only_fields = ["id", "user", "date", "product_name", "product_image"]
        extra_kwargs = {"product": {"write_only": True}}

    def get_product_image(self, obj):
        # Fetch the first related image
        image_obj = obj.product.images.first()
        request = self.context.get('request')

        if image_obj and image_obj.image and hasattr(image_obj.image, 'url'):
            return request.build_absolute_uri(image_obj.image.url) if request else image_obj.image.url
        return None
    
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
    category_name = serializers.CharField(source='category.title', read_only=True)
    vendor_name = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

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
            "category_name",
            "vendor",
            "vendor_name",
            "images",
            "last_update",
            "review_count",
            "average_rating",
        ]
        read_only_fields = ["id", "slug", "last_update", "category_name", "vendor_name", 
                          "review_count", "average_rating"]

    def get_vendor_name(self, obj):
        return obj.vendor.business_name if obj.vendor and obj.vendor.business_name else None

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg is not None else 0
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
    product_price = serializers.ReadOnlyField(source="product.unit_price")
    product_description = serializers.ReadOnlyField(source="product.description")
    vendor_id = serializers.ReadOnlyField(source="product.vendor.id")
    vendor_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = FavouriteProduct
        fields = ["id", "product", "product_title", "product_price","product_description","vendor_id", "vendor_name", "product_image","review_count",
            "average_rating", "added_at"]

    def get_vendor_name(self, obj):
        if obj.product.vendor and obj.product.vendor.business_name:
            return obj.product.vendor.business_name
        return None
    
    
    def get_product_image(self, obj):
        """Return full URL of the first product image"""
        request = self.context.get("request")
        first_image = obj.product.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None
    
    def get_review_count(self, obj):
        return obj.product.reviews.count()

    def get_average_rating(self, obj):
        avg = obj.product.reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg is not None else 0


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'message', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
        
        
#=============Deals Serializer=================
class DealSerializer(serializers.ModelSerializer):
    seller_business_name = serializers.CharField(source='seller.business_name', read_only=True)
    seller_profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = [
            'id',
            'title',
            'subtitle',
            'description',
            'image',
            'original_price',
            'discount_type',
            'discount_value',
            'final_price',
            'is_limited_time',
            'valid_until',
            'seller',
            'seller_business_name',
            'seller_profile_picture',
            'tags',
            'priority',
            'created_at'
        ]
        extra_kwargs = {
            'seller': {'write_only': True},  # Hide in response (frontend gets seller_* fields)
        }

    def get_seller_profile_picture(self, obj):
        profile_picture = obj.seller.profile_picture
        request = self.context.get('request')
        if profile_picture and hasattr(profile_picture, 'url'):
            return request.build_absolute_uri(profile_picture.url) if request else profile_picture.url
        return None

    def validate(self, data):
        """Ensure discount_value is provided for percentage/fixed deals."""
        if data['discount_type'] in [Deal.PERCENTAGE, Deal.FIXED] and not data.get('discount_value'):
            raise serializers.ValidationError("discount_value is required for this discount type.")
        return data
    
    def validate_valid_until(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            parsed = parse_datetime(value)
            if not parsed:
                raise ValidationError("Invalid datetime format for valid_until. Use ISO 8601 format.")
            return parsed
        if not isinstance(value, datetime):
            raise ValidationError("valid_until must be a string or a datetime object.")
        return value
    
class ProductMinimalSerializer(serializers.ModelSerializer):
    """For listing products that can be reviewed"""
    image = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'title', 'image', 'unit_price']
    def get_image(self, obj):
        first_image = obj.images.first()
        return first_image.image.url if first_image and first_image.image else None
class ReviewHistorySerializer(serializers.ModelSerializer):
    """For review history with product details"""
    product = ProductMinimalSerializer()
    
    class Meta:
        model = Review
        fields = ['id', 'product', 'rating', 'comment', 'date']