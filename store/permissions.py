from rest_framework.permissions import BasePermission, SAFE_METHODS

class CategoryPermission(BasePermission):
    """
    Custom permission for CategoryViewSet.
    - SAFE_METHODS (GET, HEAD, OPTIONS): Allowed for everyone.
    - POST: Allowed for authenticated users who are sellers or admins.
    - DELETE/PUT/PATCH: Allowed only for admins.
    """

    def has_permission(self, request, view):
        # Allow all safe methods (GET, HEAD, OPTIONS)
        if request.method in SAFE_METHODS:
            return True

        # Allow POST for authenticated users who are sellers or admins
        if request.method == "POST" and request.user.is_authenticated:
            return request.user.is_staff or request.user.role == "seller"

        # Allow DELETE/PUT/PATCH only for admin users
        return request.user.is_staff


