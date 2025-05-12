from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count
from .models import Product, Categories, Order, OrderItem, Cart, CartItem, Review, FavouriteProduct, Feedback
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
    CreateOrderSerializer,
    FavouriteProductSerializer,
    FeedbackSerializer,
)
from users.models import SellerProfile, CustomerProfile
from .permissions import CategoryPermission
from django.db.models import Count
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from users.serializers import SellerProfileSerializer
from notifications.utils import notify_user


class SellerProfileViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to list verified sellers with their profile information and ratings.
    """
    queryset = SellerProfile.objects.filter(verification_status=SellerProfile.VERIFIED).select_related('user')
    serializer_class = SellerProfileSerializer
    permission_classes = []  # Public access

    # Optional: Enable filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['business_name', 'user__email']
    ordering_fields = ['average_rating', 'created_at']
    
    
@extend_schema(tags=["Products API's"])
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

@extend_schema(tags=["Category APi's"])
class CategoryViewSet(viewsets.ModelViewSet):
    """
    Category ViewSet:
    - GET: Public
    - POST: Sellers and Admins
    - DELETE/PUT/PATCH: Admins only
    """

    queryset = Categories.objects.annotate(products_count=Count("products")).all()
    serializer_class = CategorySerializer
    permission_classes = [CategoryPermission]

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

    @extend_schema(
    request=CreateOrderSerializer,
    responses=OrderSerializer,
    summary="Place order from cart",
    description="Places an order based on the provided cart_id and delivery address."
)
    def create(self, request, *args, **kwargs):
        """Convert cart to order"""
        cart_id = request.data.get("cart_id")
        if not cart_id:
            return Response({"error": "cart_id is required"}, status=400)

        try:
            cart = Cart.objects.prefetch_related("items__product").get(pk=cart_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=404)

        if not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=400)

    # Prepare order data with delivery address only
        order_data = {
        "delivery_address": request.data.get("delivery_address")
        }

    # Pass request context to the serializer
        order_serializer = CreateOrderSerializer(
            data=order_data,
            context={'request': request}
        )
    
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()  # Customer is set in serializer's create method

    # Convert cart items to order items
        order_items = [
            OrderItem(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.unit_price,
            )
            for cart_item in cart.items.all()
        ]
        OrderItem.objects.bulk_create(order_items)

    # Clear the cart
        cart.delete()
        
        # Return the full order using OrderSerializer
        full_order_serializer = OrderSerializer(order)
        
        

        return Response(full_order_serializer.data, status=status.HTTP_201_CREATED)
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
    
    @extend_schema(
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "example": 1},
                "quantity": {"type": "integer", "example": 1},
                "delivery_address": {"type": "string", "example": "123 Street, City, Country"},
            },
            "required": ["product_id", "delivery_address"]
        }
    },
    responses={201: OrderSerializer},
    summary="Buy Now - Direct product order",
    description="Allows a customer to place an order for a single product directly without using the cart."
)
 
    @action(detail=False, methods=["POST"], url_path="buy-now")
    def buy_now(self, request):
        """
        Direct product purchase (Buy Now button)
        """
        user = request.user

        if not hasattr(user, "customer_profile"):
            return Response({"error": "Only customers can place orders"}, status=403)

        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        delivery_address = request.data.get("delivery_address")

        if not product_id or not delivery_address:
            return Response({"error": "product_id and delivery_address are required"}, status=400)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        # Create order
        order = Order.objects.create(
            customer=user.customer_profile,
            delivery_address=delivery_address,
        )

        # Create order item
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.unit_price,
        )

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@extend_schema(tags=["Reviews API's"])
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
    
    @action(detail=False, methods=["get"], url_path="vendor/(?P<vendor_id>[^/.]+)")
    def vendor_reviews(self, request, vendor_id=None):
        try:
            vendor = SellerProfile.objects.get(pk=vendor_id)
        except SellerProfile.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=404)

        reviews = Review.objects.filter(product__vendor=vendor)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    # def perform_create(self, serializer):
    #     """Auto-assign user and update product ratings"""
    #     product = serializer.validated_data["product"]
    #     serializer.save(user=self.request.user)

    #     # Update product rating stats
    #     avg_rating = product.reviews.aggregate(Avg("rating"))["rating__avg"]
    #     product.vendor.average_rating = avg_rating or 0
    #     product.vendor.save()


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

    
    def perform_create(self, serializer):
        user = self.request.user
        if user.is_authenticated:
            try:
                customer = CustomerProfile.objects.get(user=user)
                serializer.save(customer=customer)
            except CustomerProfile.DoesNotExist:
                raise ValidationError("Customer profile not found for this user.")
        else:
            serializer.save()  # Allow guest cart (optional)

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



@extend_schema(
    tags=["Favourite Products"],
    responses={
        200: FavouriteProductSerializer,
    },
    description="Retrieve, add, or remove favourite products. Includes product title, price, and vendor business name."
)
class FavouriteProductViewSet(viewsets.ModelViewSet):
    serializer_class = FavouriteProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavouriteProduct.objects.filter(customer=self.request.user.customer_profile)

    def create(self, request, *args, **kwargs):
        customer = request.user.customer_profile
        product_id = request.data.get("product")

        if not product_id:
            return Response({"error": "Product ID is required"}, status=400)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        fav, created = FavouriteProduct.objects.get_or_create(customer=customer, product=product)
        if not created:
            return Response({"message": "Product already in favourites"}, status=200)

        serializer = self.get_serializer(fav)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        fav = self.get_object()
        fav.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=["delete"], url_path="delete-all")
    def delete_all_favourites(self, request):
        customer = request.user.customer_profile
        deleted_count, _ = FavouriteProduct.objects.filter(customer=customer).delete()
        return Response({"message": f"Deleted {deleted_count} favourite product(s)."}, status=status.HTTP_200_OK)
   
@extend_schema(tags=["App Feedback"])
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List all feedbacks",
        description="Retrieve a list of feedbacks submitted by users. Only staff/admin users should access this endpoint.",
    )
    def list(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "You are not authorized to view feedbacks."}, status=403)
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Submit feedback",
        description="Submit a new feedback about the app. Only authenticated users can post feedback.",
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "Thank you for your feedback!"},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)