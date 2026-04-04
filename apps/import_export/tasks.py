"""
Задачи для асинхронной отправки email.
"""

import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_email_task(subject, message, recipient_list):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email отправлен: {subject}")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return {'status': 'error', 'message': str(e)}