"""
API views для админки склада (управление товарами и поставщиками)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.db.models import Q
from .models import Category, Product, SupplierProduct
from .serializers import (
    CategorySerializer,
    SupplierProductSerializer,
    SupplierProductCreateSerializer
)
from apps.users.permissions import IsSupplier, IsAdminOrSupplier
from apps.users.models import User
from apps.import_export.tasks import send_email_task


class AdminSupplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Управление поставщиками (только для администраторов)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        # Поставщики - это пользователи с user_type='supplier'
        queryset = User.objects.filter(user_type='supplier')

        # Фильтрация
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        return queryset

    def list(self, request):
        """Список поставщиков"""
        queryset = self.get_queryset()
        data = []
        for supplier in queryset:
            data.append({
                'id': supplier.id,
                'username': supplier.username,
                'email': supplier.email,
                'full_name': supplier.get_full_name(),
                'phone': supplier.phone,
                'is_active': supplier.is_active,
                'created_at': supplier.date_joined,
                'products_count': supplier.products.count(),
            })
        return Response(data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Подтверждение поставщика"""
        supplier = self.get_object()
        # Добавляем атрибут is_approved если нужно
        supplier.is_approved = True
        supplier.save()

        send_email_task.delay(
            subject=f"Поставщик {supplier.username} подтвержден",
            message=f"Ваша заявка на регистрацию одобрена!",
            recipient_list=[supplier.email]
        )
        return Response({'status': 'approved', 'supplier_id': supplier.id})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонение поставщика"""
        supplier = self.get_object()
        supplier.is_active = False
        supplier.save()

        reason = request.data.get('reason', 'Не указана причина')
        send_email_task.delay(
            subject=f"Поставщик {supplier.username} отклонен",
            message=f"Ваша заявка отклонена. Причина: {reason}",
            recipient_list=[supplier.email]
        )
        return Response({'status': 'rejected', 'supplier_id': supplier.id})

class AdminProductViewSet(viewsets.ModelViewSet):
    """
    Управление товарами (администратор и поставщики)
    """
    permission_classes = [IsAuthenticated, IsAdminOrSupplier]
    serializer_class = SupplierProductSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = SupplierProduct.objects.select_related('supplier', 'category')

        # Поставщик видит только свои товары
        if not user.is_superuser and hasattr(user, 'supplier'):
            queryset = queryset.filter(supplier=user.supplier)

        # Фильтрация по категории
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Фильтрация по поставщику
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id and user.is_superuser:
            queryset = queryset.filter(supplier_id=supplier_id)

        # Фильтрация по наличию
        in_stock = self.request.query_params.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(quantity__gt=0)

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(supplier__company_name__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """Создание товара (только для поставщиков)"""
        if not request.user.is_superuser and not hasattr(request.user, 'supplier'):
            return Response(
                {'error': 'Только поставщики могут создавать товары'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SupplierProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            product = serializer.save(
                supplier=request.user.supplier if not request.user.is_superuser else None
            )

        return Response(SupplierProductSerializer(product).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Обновление количества товара"""
        product = self.get_object()
        quantity_change = request.data.get('quantity_change', 0)

        if quantity_change > 0:
            product.increase_quantity(quantity_change)
        else:
            product.decrease_quantity(abs(quantity_change))

        return Response({
            'product_id': product.id,
            'new_quantity': product.quantity,
            'status': 'updated'
        })

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Включение/отключение товара"""
        product = self.get_object()
        product.is_active = not product.is_active
        product.save()

        return Response({
            'product_id': product.id,
            'is_active': product.is_active
        })


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Управление категориями товаров
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.all()

        # Только активные для пользователей
        if not self.request.user.is_superuser:
            queryset = queryset.filter(is_active=True)

        return queryset
