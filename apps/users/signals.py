"""
Сигналы для автоматического создания корзины при регистрации пользователя.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from django.apps import apps

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """Создает корзину для нового покупателя."""
    if created and instance.is_buyer:
        try:
            # Безопасный способ получения модели Cart
            # Не зависит от порядка загрузки приложений
            Cart = apps.get_model('orders', 'Cart')
            Cart.objects.get_or_create(user=instance)
            logger.info(f"Создана корзина для пользователя {instance.username}")
        except LookupError:
            logger.warning("Модель Cart из приложения orders еще не загружена")
        except Exception as e:
            logger.error(f"Ошибка создания корзины: {e}")