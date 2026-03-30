"""
Модели товаров и категорий.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from apps.users.models import User


class Category(models.Model):
    """
    Модель категории товара.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Название категории')
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Родительская категория')
    )

    is_active = models.BooleanField(default=True, verbose_name=_('Активна'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['name']

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class Product(models.Model):
    """
    Модель базового товара.
    """

    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name=_('Название товара')
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('Категория')
    )

    description = models.TextField(blank=True, verbose_name=_('Описание'))
    attributes = models.JSONField(default=dict, blank=True, verbose_name=_('Атрибуты'))
    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Артикул'))
    brand = models.CharField(max_length=100, blank=True, verbose_name=_('Бренд'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Товар')
        verbose_name_plural = _('Товары')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class SupplierProduct(models.Model):
    """
    Модель товара конкретного поставщика.
    Связывает базовый товар с поставщиком, добавляет цену и наличие товара.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='supplier_products',
        verbose_name=_('Товар')
    )

    supplier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'supplier'},
        related_name='products',
        verbose_name=_('Поставщик')
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Цена')
    )

    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Старая цена')
    )

    quantity = models.PositiveIntegerField(default=0, verbose_name=_('Количество'))
    external_id = models.CharField(max_length=100, blank=True, verbose_name=_('Внешний ID'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Товар поставщика')
        verbose_name_plural = _('Товары поставщиков')
        unique_together = ['product', 'supplier']
        ordering = ['product__name', 'price']

    def __str__(self) -> str:
        return f"{self.product.name} - {self.supplier.username}"

    @property
    def is_available(self) -> bool:
        return self.is_active and self.quantity > 0

    def decrease_quantity(self, amount: int) -> bool:
        if self.quantity >= amount:
            self.quantity -= amount
            if self.quantity == 0:
                self.is_active = False
            self.save()
            return True
        return False

    def increase_quantity(self, amount: int) -> None:
        self.quantity += amount
        self.is_active = True
        self.save()