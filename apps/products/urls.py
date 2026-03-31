from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, SupplierProductViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('supplier-products', SupplierProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
]