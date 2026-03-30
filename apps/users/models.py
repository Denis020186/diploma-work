"""
Модель пользователя для системы автоматизации закупок.

Модель добавляет:
- Тип пользователя (покупатель или поставщик)
- Контактный телефон
- Название компании (для поставщиков)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Расширенная модель пользователя.

    Attributes:
        user_type (str): Тип пользователя - 'buyer' или 'supplier'
        email (str): Email адрес (уникальный)
        phone (str): Контактный телефон
        company_name (str): Название компании (для поставщиков)
    """

    # Типы пользователей
    USER_TYPES = (
        ('buyer', _('Покупатель')),  # Обычный покупатель
        ('supplier', _('Поставщик')),  # Поставщик товаров
    )

    # Поле типа пользователя
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPES,
        default='buyer',
        verbose_name=_('Тип пользователя'),
        help_text=_('Выберите тип учетной записи')
    )

    # Email - используется для входа и уведомлений
    email = models.EmailField(
        unique=True,
        verbose_name=_('Электронная почта'),
        help_text=_('Введите действующий email для уведомлений')
    )

    # Телефон - необязательное поле
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Телефон'),
        help_text=_('Контактный телефон (необязательно)')
    )

    # Название компании - обязательно для поставщиков
    company_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Название компании'),
        help_text=_('Для поставщиков обязательно указать название компании')
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['-date_joined']

    def __str__(self) -> str:
        return self.username

    @property
    def is_supplier(self) -> bool:
        return self.user_type == 'supplier'

    @property
    def is_buyer(self) -> bool:
        return self.user_type == 'buyer'

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
        