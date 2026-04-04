"""
Celery задачи для заказов
"""

import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task(name='apps.orders.tasks.process_order')
def process_order(order_id):
    """
    Асинхронная обработка заказа

        order_id: ID заказа для обработки
    """
    from .models import Order

    try:
        order = Order.objects.get(id=order_id)

        # Логика обработки заказа
        logger.info(f"Начинаем обработку заказа #{order.id}")

        # Обновляем статус
        order.status = 'confirmed'
        order.save()

        # Отправляем уведомление
        from apps.import_export.tasks import send_email_task
        send_email_task.delay(
            subject=f"Заказ #{order.id} подтвержден",
            message=f"Ваш заказ #{order.id} успешно подтвержден и передан в обработку.",
            recipient_list=[order.user.email]
        )

        logger.info(f"Заказ #{order.id} успешно обработан")
        return {'status': 'success', 'order_id': order.id}

    except Order.DoesNotExist:
        logger.error(f"Заказ #{order_id} не найден")
        return {'status': 'error', 'message': 'Order not found'}
    except Exception as e:
        logger.error(f"Ошибка обработки заказа #{order_id}: {e}")
        return {'status': 'error', 'message': str(e)}

@shared_task(name='apps.orders.tasks.update_order_status')
def update_order_status(order_id, new_status):
    """
    Асинхронное обновление статуса заказа

        order_id: ID заказа
        new_status: Новый статус
    """
    from .models import Order

    try:
        order = Order.objects.get(id=order_id)
        old_status = order.status
        order.status = new_status
        order.save()

        from apps.import_export.tasks import send_email_task
        send_email_task.delay(
            subject=f"Статус заказа #{order.id} изменен",
            message=f"Статус вашего заказа #{order.id} изменен с '{old_status}' на '{new_status}'.",
            recipient_list=[order.user.email]
        )

        return {'status': 'success', 'order_id': order.id, 'old_status': old_status, 'new_status': new_status}

    except Order.DoesNotExist:
        return {'status': 'error', 'message': 'Order not found'}