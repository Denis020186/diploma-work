"""
API views для админки заказов
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q, Sum
from .models import Order, OrderItem, OrderStatus
from .serializers import OrderSerializer, OrderStatusUpdateSerializer
from apps.users.permissions import IsAdminOrSupplier
from apps.import_export.tasks import send_email_task

class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Управление заказами (администратор и поставщики)
    """
    permission_classes = [IsAuthenticated, IsAdminOrSupplier]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related('user').prefetch_related('items__supplier_product')

        if not user.is_superuser and (hasattr(user, 'is_supplier') and user.is_supplier):
            # У пользователя есть связанный профиль поставщика
            if hasattr(user, 'supplier_profile'):
                queryset = queryset.filter(
                    items__supplier_product__supplier=user.supplier_profile
                ).distinct()
            # Если есть поле supplier
            elif hasattr(user, 'supplier'):
                queryset = queryset.filter(
                    items__supplier_product__supplier=user.supplier
                ).distinct()

        # Фильтрация по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Фильтрация по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Поиск по номеру заказа или email пользователя
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search)
            )

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Обновление статуса заказа"""
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        comment = serializer.validated_data.get('comment', '')

        with transaction.atomic():
            old_status = order.status
            order.status = new_status
            order.save()

            # Изменение статуса
            OrderStatus.objects.create(
                order=order,
                status=new_status,
                comment=comment,
                changed_by=request.user
            )

            # Отправка email уведомления
            if new_status in ['confirmed', 'shipped', 'delivered', 'cancelled']:
                send_email_task.delay(
                    subject=f"Статус заказа #{order.id} изменен",
                    message=f"Статус вашего заказа #{order.id} изменен на: {order.get_status_display()}",
                    recipient_list=[order.user.email]
                )

        return Response({
            'order_id': order.id,
            'old_status': old_status,
            'new_status': new_status,
            'message': f'Статус заказа изменен на {order.get_status_display()}'
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по заказам"""
        user = request.user

        if user.is_superuser:
            orders = Order.objects.all()
        elif hasattr(user, 'is_supplier') and user.is_supplier:
            if hasattr(user, 'supplier_profile'):
                orders = Order.objects.filter(
                    items__supplier_product__supplier=user.supplier_profile
                ).distinct()
            elif hasattr(user, 'supplier'):
                orders = Order.objects.filter(
                    items__supplier_product__supplier=user.supplier
                ).distinct()
            else:
                return Response({'error': 'Профиль поставщика не найден'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)

        statistics = {
            'total_orders': orders.count(),
            'by_status': {},
            'total_amount': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'average_order_amount': 0
        }

        # Статистика по статусам
        for status_code, status_name in Order.STATUS_CHOICES:
            count = orders.filter(status=status_code).count()
            if count > 0:
                statistics['by_status'][status_code] = {
                    'name': status_name,
                    'count': count
                }

        if statistics['total_orders'] > 0:
            statistics['average_order_amount'] = statistics['total_amount'] / statistics['total_orders']

        return Response(statistics)


    @action(detail=True, methods=['get'])
    def status_history(self, request, pk=None):
        """История статусов заказа"""
        order = self.get_object()
        status_history = order.status_history.all().order_by('-created_at')

        data = [{
            'id': item.id,
            'status': item.status,
            'status_display': item.get_status_display(),
            'comment': item.comment,
            'created_at': item.created_at,
            'changed_by': item.changed_by.email if item.changed_by else 'Система'
        } for item in status_history]

        return Response(data)