"""
Модели заказов и корзины.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from apps.users.models import User
from apps.products.models import SupplierProduct


class Cart(models.Model):
    """Модель корзины пользователя."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name=_('Пользователь')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Корзина')
        verbose_name_plural = _('Корзины')
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f"Корзина {self.user.username}"

    @property
    def total_amount(self) -> Decimal:
        total = sum(item.total_price for item in self.items.all())
        return Decimal(str(total))

    def clear(self) -> None:
        self.items.all().delete()


class CartItem(models.Model):
    """Модель позиции в корзине."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Корзина')
    )

    supplier_product = models.ForeignKey(
        SupplierProduct,
        on_delete=models.CASCADE,
        verbose_name=_('Товар поставщика')
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество')
    )

    class Meta:
        verbose_name = _('Позиция корзины')
        verbose_name_plural = _('Позиции корзины')
        unique_together = ['cart', 'supplier_product']

    def __str__(self) -> str:
        return f"{self.supplier_product.product.name} x {self.quantity}"

    @property
    def total_price(self) -> Decimal:
        return self.supplier_product.price * self.quantity


class Order(models.Model):
    """Модель заказа."""

    STATUS_CHOICES = (
        ('pending', _('В обработке')),
        ('confirmed', _('Подтверждён')),
        ('shipped', _('Отправлен')),
        ('delivered', _('Доставлен')),
        ('cancelled', _('Отменён')),
    )
    STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_('Покупатель')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Статус')
    )

    delivery_address = models.TextField(verbose_name=_('Адрес доставки'))
    delivery_city = models.CharField(max_length=100, verbose_name=_('Город'))
    delivery_postal_code = models.CharField(max_length=20, verbose_name=_('Почтовый индекс'))
    comment = models.TextField(blank=True, verbose_name=_('Комментарий'))

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Общая сумма')
    )

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Заказ #{self.id} - {self.user.username}"

    @property
    def can_cancel(self) -> bool:
        return self.status in ['pending', 'confirmed']

    def calculate_total(self) -> Decimal:
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


class OrderItem(models.Model):
    """Модель позиции заказа с фиксированной ценой."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заказ')
    )

    supplier_product = models.ForeignKey(
        SupplierProduct,
        on_delete=models.CASCADE,
        verbose_name=_('Товар поставщика')
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество')
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Цена на момент заказа')
    )

    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказов')
        unique_together = ['order', 'supplier_product']

    def __str__(self) -> str:
        return f"{self.supplier_product.product.name} x {self.quantity}"

    @property
    def total_price(self) -> Decimal:
        return self.price * self.quantity


class OrderStatus(models.Model):
    """Модель для отслеживания истории статусов заказа."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_('Заказ')
    )

    status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        verbose_name=_('Статус')
    )

    comment = models.TextField(
        blank=True,
        verbose_name=_('Комментарий')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Время изменения')
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changed_statuses',
        verbose_name=_('Кто изменил')
    )

    class Meta:
        verbose_name = _('История статуса заказа')
        verbose_name_plural = _('Истории статусов заказов')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Заказ #{self.order.id} - {self.get_status_display()} в {self.created_at}"