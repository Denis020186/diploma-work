from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer, OrderCreateSerializer
from apps.products.models import SupplierProduct


class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        cart = self.get_object()
        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        try:
            supplier_product = SupplierProduct.objects.get(id=product_id, is_active=True)
            if supplier_product.quantity < quantity:
                return Response({'error': f'Доступно только {supplier_product.quantity}'}, status=400)
        except SupplierProduct.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=404)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, supplier_product=supplier_product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response(CartItemSerializer(cart_item).data, status=201)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart = self.get_object()
        item_id = request.data.get('item_id')

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            return Response({'message': 'Товар удален'}, status=200)
        except CartItem.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=404)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        cart = self.get_object()

        if not cart.items.exists():
            return Response({'error': 'Корзина пуста'}, status=400)

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                delivery_address=serializer.validated_data['delivery_address'],
                delivery_city=serializer.validated_data['delivery_city'],
                delivery_postal_code=serializer.validated_data['delivery_postal_code'],
                comment=serializer.validated_data.get('comment', '')
            )

            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    supplier_product=cart_item.supplier_product,
                    quantity=cart_item.quantity,
                    price=cart_item.supplier_product.price
                )
                cart_item.supplier_product.decrease_quantity(cart_item.quantity)

            order.calculate_total()
            cart.clear()

        return Response(OrderSerializer(order).data, status=201)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_supplier:
            return Order.objects.filter(items__supplier_product__supplier=self.request.user).distinct()
        return Order.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.user != request.user:
            return Response({'error': 'Вы можете отменять только свои заказы'}, status=403)

        if not order.can_cancel:
            return Response({'error': 'Невозможно отменить заказ в текущем статусе'}, status=400)

        for item in order.items.all():
            item.supplier_product.increase_quantity(item.quantity)

        order.status = 'cancelled'
        order.save()

        return Response(OrderSerializer(order).data)