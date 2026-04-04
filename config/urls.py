"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from apps.products.admin_views import (AdminSupplierViewSet, AdminProductViewSet, CategoryViewSet)
from apps.orders.admin_views import AdminOrderViewSet


admin_router = DefaultRouter()
admin_router.register(r'suppliers', AdminSupplierViewSet, basename='admin-suppliers')
admin_router.register(r'products', AdminProductViewSet, basename='admin-products')
admin_router.register(r'categories', CategoryViewSet, basename='categories')
admin_router.register(r'orders', AdminOrderViewSet, basename='admin-orders')

schema_view = get_schema_view(
    openapi.Info(
        title="Purchase Automation API",
        default_version='v1',
        description="API для автоматизации закупок",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/', include('apps.products.urls')),
    path('api/v1/', include('apps.orders.urls')),
    path('api/v1/admin/', include(admin_router.urls)),
    path('api/v1/import-export/', include('apps.import_export.urls')),
    
    # Swagger документация
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
    path('', RedirectView.as_view(url='/swagger/', permanent=False)),
]

# Обслуживание статики в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
