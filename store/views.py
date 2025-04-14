from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count
from .models import Product, Categories, Order, OrderItem, Cart, CartItem, Review
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    OrderSerializer,
    OrderItemSerializer,
    CartSerializer,
    CartItemSerializer,
    ReviewSerializer,
    SellerProductSerializer,
    OrderStatusUpdateSerializer,
)
from users.models import SellerProfile


class ProductViewSet(viewsets.ModelViewSet):
    """
    Handles Product CRUD operations with vendor-specific restrictions
    """

    queryset = Product.objects.prefetch_related("images").select_related(
        "vendor", "category"
    )
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "vendor"]
    search_fields = ["title", "description"]
    ordering_fields = ["unit_price", "last_update"]

    def get_serializer_context(self):
        """Inject request context for image URL generation"""
        return {"request": self.request}

    def get_permissions(self):
        """Vendors can only modify their own products"""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated()]
        return []

    def get_queryset(self):
        """Filter products based on user role"""
        queryset = super().get_queryset()

        # For sellers, only show their own products
        if hasattr(self.request.user, "seller_profile"):
            return queryset.filter(vendor=self.request.user.seller_profile)

        # For customers/admins, show all available products
        return queryset

    def perform_create(self, serializer):
        """Auto-assign vendor from logged-in seller"""
        if hasattr(self.request.user, "seller_profile"):
            serializer.save(vendor=self.request.user.seller_profile)
        else:
            raise PermissionDenied("Only sellers can create products")

    @action(detail=False, methods=["GET"], url_path="seller-products")
    def seller_products(self, request):
        """Special endpoint for seller dashboard with extended product stats"""
        if not hasattr(request.user, "seller_profile"):
            return Response({"error": "Only sellers can access this"}, status=403)

        queryset = self.get_queryset().filter(vendor=request.user.seller_profile)
        serializer = SellerProductSerializer(queryset, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Handles Category CRUD (Admin only)
    """

    queryset = Categories.objects.annotate(products_count=Count("products")).all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of categories with products"""
        category = self.get_object()
        if category.products.count() > 0:
            return Response(
                {"error": "Category contains products and cannot be deleted"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Handles Order lifecycle with role-based access
    """

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Customers see their orders, sellers see orders for their products"""
        queryset = Order.objects.prefetch_related("items__product")

        if hasattr(self.request.user, "customer_profile"):
            return queryset.filter(customer=self.request.user.customer_profile)

        elif hasattr(self.request.user, "seller_profile"):
            return queryset.filter(
                items__product__vendor=self.request.user.seller_profile
            ).distinct()

        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Convert cart to order"""
        cart = Cart.objects.prefetch_related("items__product").get(
            pk=request.data.get("cart_id")
        )

        if not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        order_data = {
            "customer": request.user.customer_profile,
            "delivery_address": request.data.get("delivery_address"),
        }

        order_serializer = self.get_serializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()

        # Convert cart items to order items
        order_items = []
        for cart_item in cart.items.all():
            order_items.append(
                OrderItem(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.product.unit_price,
                )
            )

        OrderItem.objects.bulk_create(order_items)
        cart.delete()  # Clear the cart

        return Response(order_serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=["PATCH"], serializer_class=OrderStatusUpdateSerializer
    )
    def update_status(self, request, pk=None):
        """Special endpoint for status updates (for sellers)"""
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Handles Product Reviews with auto-user assignment
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter reviews by product or user"""
        queryset = Review.objects.select_related("user", "product")

        if "product_pk" in self.kwargs:
            return queryset.filter(product_id=self.kwargs["product_pk"])

        if hasattr(self.request.user, "customer_profile"):
            return queryset.filter(user=self.request.user)

        return queryset.none()

    def perform_create(self, serializer):
        """Auto-assign user and update product ratings"""
        product = serializer.validated_data["product"]
        serializer.save(user=self.request.user)

        # Update product rating stats
        avg_rating = product.reviews.aggregate(Avg("rating"))["rating__avg"]
        product.vendor.average_rating = avg_rating or 0
        product.vendor.save()


class CartViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Handles Cart operations (create, view, delete)
    """

    queryset = Cart.objects.prefetch_related("items__product").all()
    serializer_class = CartSerializer


class CartItemViewSet(viewsets.ModelViewSet):
    """
    Handles Cart Items with custom logic for add/update
    """

    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs["cart_pk"]).select_related(
            "product"
        )

    def get_serializer_context(self):
        """Inject cart ID from URL"""
        return {"cart_id": self.kwargs["cart_pk"]}

    def create(self, request, *args, **kwargs):
        """Custom create to handle quantity increments"""
        cart_id = self.kwargs["cart_pk"]
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            cart_item = CartItem.objects.get(cart_id=cart_id, product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data)
        except CartItem.DoesNotExist:
            return super().create(request, *args, **kwargs)
