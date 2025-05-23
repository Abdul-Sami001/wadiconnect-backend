from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Notification, UserDevice
from .serializers import NotificationSerializer
from rest_framework.pagination import PageNumberPagination
from .utils import notify_user
from store.models import Order, Review 
from .serializers import SuccessResponseSerializer
from .serializers import UserDeviceSerializer


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
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     order_id = self.request.query_params.get('order_id')
        
    #     if order_id:
    #         queryset = queryset.filter(
    #             order_details__order_id=order_id
    #         )
    #     return queryset

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
            product_ids = [str(item.product.id) for item in order.items.all()]
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        notify_user(
            order.customer.user,
            f"Order #{order.id} is delayed. We apologize!",
            'delivery_delay',
            
                {  # ✅ Add product_ids to payload
                    'order_id': order.id,
                    'product_ids': product_ids,
                    'estimated_delay': '15 minutes'  # Optional contextual data
                }
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
class DeviceRegistrationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDeviceSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get('platform'):
            return Response({"error": "Platform is required"}, status=400)
        

        UserDevice.objects.filter(
            token=serializer.validated_data['token']
        ).delete()
        
        device = serializer.save(user=request.user)
        return Response({"status": "Device registered"}, status=201)

    def delete(self, request):
        token = request.data.get('token')
        UserDevice.objects.filter(user=request.user, token=token).delete()
        return Response({"status": "Device unregistered"})
class OrderNotificationsAPI(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        order_id = self.kwargs['order_id']
        return Notification.objects.filter(user=self.request.user, payload__order_id=order_id)
