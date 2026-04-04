"""
Celery задачи для пользователей
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from apps.import_export.tasks import send_email_task

logger = logging.getLogger(__name__)

@shared_task(name='apps.users.tasks.cleanup_old_sessions')
def cleanup_old_sessions():
    """
    Очистка старых сессий (периодическая задача)
    """
    # Удаляем сессии старше 7 дней
    threshold = timezone.now() - timedelta(days=7)
    old_sessions = Session.objects.filter(expire_date__lt=threshold)
    count = old_sessions.count()
    old_sessions.delete()

    logger.info(f"Удалено {count} старых сессий")

    return {
        'status': 'success',
        'deleted_sessions': count
    }

@shared_task(name='apps.users.tasks.send_welcome_email')
def send_welcome_email(user_id):
    """
    Отправка приветственного email новому пользователю
    """
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        send_email_task.delay(
            subject="Добро пожаловать в Purchase Automation!",
            message=(
                f"Здравствуйте, {user.username}!\n\n"
                f"Рады приветствовать вас в системе автоматизации закупок.\n\n"
                f"Здесь вы можете:\n"
                f"• Просматривать товары\n"
                f"• Оформлять заказы\n"
                f"• Отслеживать статус доставки\n\n"
                f"С уважением,\n"
                f"Команда Purchase Automation"
            ),
            recipient_list=[user.email]
        )

        return {'status': 'success', 'user_id': user_id}

    except Exception as e:
        logger.error(f"Ошибка отправки приветственного email: {e}")
        return {'status': 'error', 'message': str(e)}