from django.contrib import admin
from .models import Category, Product, SupplierProduct


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'brand', 'sku', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku', 'brand')


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'supplier', 'price', 'quantity', 'is_available')
    list_filter = ('supplier', 'is_active')
    search_fields = ('product__name', 'supplier__username')

    def is_available(self, obj):
        return obj.is_available

    is_available.boolean = True
    is_available.short_description = 'В наличии'