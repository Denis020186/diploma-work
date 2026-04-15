from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderStatus
from apps.products.serializers import SupplierProductSerializer
import re


class CartItemSerializer(serializers.ModelSerializer):
    product_details = SupplierProductSerializer(source='supplier_product', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ('id', 'supplier_product', 'product_details', 'quantity', 'total_price')


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'total_amount', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class OrderCreateSerializer(serializers.Serializer):
    delivery_address = serializers.CharField(max_length=500)
    delivery_city = serializers.CharField(max_length=100)
    delivery_postal_code = serializers.CharField(max_length=20)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_delivery_postal_code(self, value):
        if not value.strip().isdigit() or len(value.strip()) != 6:
            raise serializers.ValidationError("Почтовый индекс должен состоять из 6 цифр")
        return value.strip()

    def validate_delivery_city(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Минимум 2 символа")
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', value):
            raise serializers.ValidationError("Только буквы, пробелы, дефисы")
        return value.title()


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='supplier_product.product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'supplier_product', 'product_name', 'quantity', 'price', 'total_price')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'user', 'created_at', 'updated_at', 'status', 'status_display',
                  'delivery_address', 'delivery_city', 'delivery_postal_code', 'comment',
                  'total_amount', 'items')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'total_amount')


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'shipped', 'delivered', 'cancelled'],
        help_text="Новый статус заказа"
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Комментарий к изменению статуса"
    )


class OrderStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)

    class Meta:
        model = OrderStatus
        fields = ('id', 'order', 'status', 'status_display', 'comment', 'created_at', 'changed_by', 'changed_by_email')
        read_only_fields = ('id', 'created_at')