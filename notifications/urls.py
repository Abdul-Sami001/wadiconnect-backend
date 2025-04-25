from django.urls import path
from .api import NotificationListAPI, NotificationDetailAPI, MarkAllAsReadAPI

urlpatterns = [
    path('', NotificationListAPI.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailAPI.as_view(), name='notification-detail'),
    path('mark-all-read/', MarkAllAsReadAPI.as_view(), name='mark-all-read'),
]