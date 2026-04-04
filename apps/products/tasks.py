"""
Celery задачи для управления товарами
"""

import logging
from celery import shared_task
from django.db.models import Q
from .models import SupplierProduct
from apps.import_export.tasks import send_email_task

logger = logging.getLogger(__name__)

@shared_task(name='apps.products.tasks.update_prices')
def update_prices(product_ids, price_change_percent):
    """
    Массовое обновление цен

        product_ids: Список ID товаров поставщика
        price_change_percent: Процент изменения цены
    """

    updated_count = 0
    errors = []

    for product_id in product_ids:
        try:
            product = SupplierProduct.objects.get(id=product_id)
            old_price = product.price
            new_price = old_price * (1 + price_change_percent / 100)
            product.price = new_price
            product.old_price = old_price
            product.save()
            updated_count += 1

            logger.info(f"Цена товара #{product_id} изменена: {old_price} -> {new_price}")

        except SupplierProduct.DoesNotExist:
            errors.append(f"Товар #{product_id} не найден")
            logger.error(f"Товар #{product_id} не найден")
        except Exception as e:
            errors.append(f"Ошибка обновления товара #{product_id}: {str(e)}")
            logger.error(f"Ошибка обновления товара #{product_id}: {e}")

    return {
        'status': 'success',
        'updated_count': updated_count,
        'total': len(product_ids),
        'price_change_percent': price_change_percent,
        'errors': errors
    }

@shared_task(name='apps.products.tasks.check_low_stock')
def check_low_stock():
    """
    Проверка товаров с низким остатком
    """

    threshold = 10

    low_stock_products = SupplierProduct.objects.filter(
        quantity__lte=threshold,
        quantity__gt=0,
        is_active=True
    ).select_related('product', 'supplier')

    out_of_stock_products = SupplierProduct.objects.filter(
        quantity=0,
        is_active=True
    ).select_related('product', 'supplier')

    # Отправка уведомлений о низком остатке
    for product in low_stock_products:
        send_email_task.delay(
            subject=f"⚠️ Низкий остаток: {product.product.name}",
            message=(
                f"Уважаемый поставщик {product.supplier.username}!\n\n"
                f"Товар: {product.product.name}\n"
                f"Остаток: {product.quantity} шт.\n"
                f"Порог: {threshold} шт.\n\n"
                f"Пожалуйста, пополните запасы."
            ),
            recipient_list=[product.supplier.email]
        )

    # Отправка уведомлений о товарах закончившихся
    for product in out_of_stock_products:
        send_email_task.delay(
            subject=f"❌ Товар закончился: {product.product.name}",
            message=(
                f"Уважаемый поставщик {product.supplier.username}!\n\n"
                f"Товар: {product.product.name}\n"
                f"Остаток: 0 шт.\n\n"
                f"Требуется срочное пополнение!"
            ),
            recipient_list=[product.supplier.email]
        )

    return {
        'status': 'success',
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count()
    }