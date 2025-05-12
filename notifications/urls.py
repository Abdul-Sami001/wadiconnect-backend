from django.urls import path
from .api import (
    NotificationListAPI,
    NotificationDetailAPI,
    MarkAllAsReadAPI,
    DeliveryDelayAPI,   # ✅ Import added
    RestaurantReplyAPI,
    ClearAllNotificationsAPI,
    DeviceRegistrationAPI,
    OrderNotificationsAPI    
)

urlpatterns = [
    path('', NotificationListAPI.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailAPI.as_view(), name='notification-detail'),
    path('mark-all-read/', MarkAllAsReadAPI.as_view(), name='mark-all-read'),
    path('delivery-delay/<int:order_id>/', DeliveryDelayAPI.as_view(), name='delivery-delay'),
    path('restaurant-reply/<int:review_id>/', RestaurantReplyAPI.as_view(), name='restaurant-reply'),
    path('clear/', ClearAllNotificationsAPI.as_view(), name='notification-clear'),
    path('devices/', DeviceRegistrationAPI.as_view(), name='device-registration'),
    path('order/<int:order_id>/', OrderNotificationsAPI.as_view(), name='order-notifications'),

]