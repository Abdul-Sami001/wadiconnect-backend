from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.pagination import PageNumberPagination
from .utils import notify_user
from store.models import Order, Review 
from .serializers import SuccessResponseSerializer

class NotificationPagination(PageNumberPagination):
    page_size = 10

class NotificationListAPI(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        return queryset

class NotificationDetailAPI(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(is_read=True)

class MarkAllAsReadAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SuccessResponseSerializer
    
    def post(self, request):
        count = Notification.objects.mark_all_as_read(request.user)
        return Response({'status': 'success', 'marked_read': count})
    
    
# 🚚 Delivery Delay Notification API
class DeliveryDelayAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SuccessResponseSerializer# Only admins can delay deliveries

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        notify_user(
            order.customer.user,
            f"Order #{order.id} is delayed. We apologize!",
            'delivery_delay',
            {'order_id': order.id}
        )
        return Response({'status': 'Delivery delay notification sent successfully'})

# 📝 Restaurant Reply Notification API
class RestaurantReplyAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SuccessResponseSerializer # Seller must be logged in

    def post(self, request, review_id):
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({'error': 'Review not found'}, status=404)

        if hasattr(review.product, 'vendor') and review.product.vendor and review.product.vendor.user == request.user:
            # Only the vendor who owns the product can reply
            notify_user(
                review.user,
                f"{review.product.vendor.business_name} replied to your review!",
                'restaurant_reply',
                {'review_id': review_id}
            )
            return Response({'status': 'Restaurant reply notification sent successfully'})
        else:
            return Response({'error': 'Unauthorized: You cannot reply to this review.'}, status=403)
        

class ClearAllNotificationsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SuccessResponseSerializer

    def delete(self, request):
        deleted, _ = Notification.objects.filter(user=request.user).delete()
        return Response({'status': 'success', 'deleted': deleted})