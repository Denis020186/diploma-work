from rest_framework import serializers
from .models import Category, Product, SupplierProduct


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категории"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'parent_name', 'is_active', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор для базового товара"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'description',
                  'attributes', 'brand', 'sku', 'is_active', 'created_at']


class SupplierProductSerializer(serializers.ModelSerializer):
    """Сериализатор для товара поставщика"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.username', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupplierProduct
        fields = ['id', 'product', 'product_name', 'product_sku', 'category_name',
                  'supplier', 'supplier_name', 'price', 'old_price', 'quantity',
                  'external_id', 'is_active', 'is_available', 'created_at', 'updated_at']


class SupplierProductCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания товара поставщиком"""
    product_name = serializers.CharField(write_only=True, required=True)
    category_id = serializers.IntegerField(write_only=True, required=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sku = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = SupplierProduct
        fields = ['product_name', 'category_id', 'description', 'sku',
                  'price', 'quantity', 'external_id']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше 0")
        return value

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Количество не может быть отрицательным")
        return value