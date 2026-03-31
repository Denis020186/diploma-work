from rest_framework import serializers
from .models import Category, Product, SupplierProduct


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'parent', 'is_active')


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'category_name', 'description',
                  'attributes', 'brand', 'sku', 'is_active')


class SupplierProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.username', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupplierProduct
        fields = ('id', 'product', 'product_name', 'supplier', 'supplier_name',
                  'price', 'quantity', 'is_available')