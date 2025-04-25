from .models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        return {
               'unread_notifications': unread_qs[:5],
               'unread_count': unread_qs.count()
            # 'unread_notifications': Notification.objects.unread().filter(user=request.user)[:5],
            # 'unread_count': Notification.objects.unread().filter(user=request.user).count()
        }
    return {}