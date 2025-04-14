from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

# Main router for top-level resources
router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="products")
router.register("categories", views.CategoryViewSet, basename="categories")
router.register("orders", views.OrderViewSet, basename="orders")
router.register("carts", views.CartViewSet, basename="carts")
router.register("reviews", views.ReviewViewSet, basename="reviews")

# Nested router for cart items
cart_router = routers.NestedSimpleRouter(router, r"carts", lookup="cart")
cart_router.register(r"items", views.CartItemViewSet, basename="cart-items")

# Nested router for product reviews (optional approach)
product_router = routers.NestedSimpleRouter(router, r"products", lookup="product")
product_router.register(r"reviews", views.ReviewViewSet, basename="product-reviews")

urlpatterns = [
    # Main API routes
    path("", include(router.urls)),
    # Nested routes
    path("", include(cart_router.urls)),
    path("", include(product_router.urls)),
    # Additional custom endpoints
    path(
        "products/seller-products/",
        views.ProductViewSet.as_view({"get": "seller_products"}),
        name="seller-products",
    ),
]

# For Swagger/OpenAPI documentation
app_name = "store"
