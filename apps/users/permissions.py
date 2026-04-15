"""
Разрешения для доступа к API
"""

from rest_framework import permissions


class IsAdminOrSupplier(permissions.BasePermission):
    """Разрешение для администратора или поставщика"""

    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                (request.user.is_superuser or request.user.user_type == 'supplier'))

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        # Поставщик может работать только со своими объектами
        if request.user.user_type == 'supplier':
            if hasattr(obj, 'items'):
                from apps.orders.models import OrderItem
                has_supplier_items = OrderItem.objects.filter(
                    order=obj,
                    supplier_product__supplier__user=request.user
                ).exists()
                if has_supplier_items:
                    return True
            if hasattr(obj, 'supplier'):
                if hasattr(obj.supplier, 'user'):
                    return obj.supplier.user == request.user
                return obj.supplier == request.user
            if hasattr(obj, 'user'):
                return obj.user == request.user
            if hasattr(obj, 'supplier_id'):
                if hasattr(request.user, 'supplier_profile'):
                    return obj.supplier_id == request.user.supplier_profile.id
                return obj.supplier_id == request.user.id

        return False


class IsSupplier(permissions.BasePermission):
    """Разрешение только для поставщиков"""

    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                request.user.user_type == 'supplier')


class IsAdminUser(permissions.BasePermission):
    """Разрешение только для администраторов"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser