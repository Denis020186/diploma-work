"""
Celery задачи для импорта/экспорта данных и отправки email
"""

import logging
import csv
import io
import base64
from datetime import datetime
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.products.models import SupplierProduct, Product, Category
from apps.users.models import User as SupplierModel
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)

# EMAIL ЗАДАЧИ

@shared_task(name='apps.import_export.tasks.send_email_task', queue='email')
def send_email_task(subject, message, recipient_list, html_message=None):
    """
    Асинхронная отправка email

        subject: Тема письма
        message: Текст письма
        recipient_list: Список получателей
        html_message: HTML версия письма
    """
    try:
        if isinstance(recipient_list, str):
            recipient_list = [recipient_list]

        sent = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message
        )

        logger.info(f"Email успешно отправлен: {subject} -> {recipient_list}")
        return {
            'status': 'success',
            'subject': subject,
            'recipients': recipient_list,
            'sent_count': sent
        }
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return {'status': 'error', 'message': str(e)}

# ЗАДАЧИ ИМПОРТА

@shared_task(name='apps.import_export.tasks.do_import', queue='import', bind=True)
def do_import(self, file_content, filename, model_name, user_id):
    """
    Асинхронный импорт данных

        file_content: Содержимое файла (base64 строка)
        filename: Имя файла
        model_name: Название модели (products, suppliers)
        user_id: ID пользователя, запустившего импорт
    """
    User = get_user_model()

    try:
        # Получаем пользователя для уведомлений
        user = User.objects.get(id=user_id)

        # Обновляем статус задачи
        self.update_state(state='PROGRESS', meta={
            'current': 0,
            'total': 100,
            'status': 'Начинаем импорт...'
        })

        # Декодируем содержимое файла
        if isinstance(file_content, str):
            file_bytes = base64.b64decode(file_content)
        else:
            file_bytes = file_content

        # Определяем тип файла
        file_extension = filename.split('.')[-1].lower()

        # Читаем CSV файл
        if file_extension == 'csv':
            data = pd.read_csv(BytesIO(file_bytes))
        elif file_extension in ['xls', 'xlsx']:
            data = pd.read_excel(BytesIO(file_bytes))
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_extension}")

        total_rows = len(data)

        self.update_state(state='PROGRESS', meta={
            'current': 0,
            'total': total_rows,
            'status': f'Загружено {total_rows} записей'
        })

        # Статистика импорта
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        # Импорт в зависимости от модели
        with transaction.atomic():
            for index, row in data.iterrows():
                try:
                    if model_name == 'products':
                        result = _import_product_row(row)
                    elif model_name == 'suppliers':
                        result = _import_supplier_row(row)
                    else:
                        raise ValueError(f"Неизвестная модель: {model_name}")

                    if result.get('action') == 'created':
                        stats['created'] += 1
                    else:
                        stats['updated'] += 1

                    # Обновляем прогресс каждые 10 строк
                    if index % 10 == 0:
                        self.update_state(state='PROGRESS', meta={
                            'current': index + 1,
                            'total': total_rows,
                            'status': f'Импортировано {index + 1} из {total_rows}'
                        })

                except Exception as e:
                    stats['errors'] += 1
                    stats['error_details'].append({
                        'row': index + 1,
                        'error': str(e)
                    })
                    logger.error(f"Ошибка импорта строки {index + 1}: {e}")

        # Отправляем уведомление пользователю
        send_email_task.delay(
            subject=f"Импорт {model_name} завершен",
            message=(
                f"Импорт данных завершен!\n\n"
                f"✅ Создано: {stats['created']}\n"
                f"🔄 Обновлено: {stats['updated']}\n"
                f"❌ Ошибок: {stats['errors']}\n\n"
                f"📊 Всего обработано: {total_rows} строк"
            ),
            recipient_list=[user.email]
        )

        return {
            'status': 'success',
            'stats': stats,
            'total_rows': total_rows
        }

    except Exception as e:
        logger.error(f"Ошибка импорта: {e}")
        send_email_task.delay(
            subject=f"❌ Ошибка импорта {model_name}",
            message=f"Произошла ошибка при импорте: {str(e)}",
            recipient_list=[user.email]
        )
        return {'status': 'error', 'message': str(e)}

def _import_product_row(row):
    """Импорт одной строки товара"""
    name = row.get('name')
    sku = str(row.get('sku', ''))
    price = float(row.get('price', 0))
    quantity = int(row.get('quantity', 0))
    supplier_name = row.get('supplier')
    category_name = row.get('category', 'Общая')

    # Находим или создаем категорию
    category, _ = Category.objects.get_or_create(name=category_name)

    # Находим или создаем поставщика
    supplier, _ = SupplierModel.objects.get_or_create(
        username=supplier_name,
        defaults={
            'user_type': 'supplier',
            'email': f'{supplier_name}@example.com'
        }
    )

    # Создаем или обновляем товар
    product, created = Product.objects.get_or_create(
        sku=sku,
        defaults={
            'name': name,
            'category': category,
            'description': row.get('description', ''),
        }
    )

    # Если товар уже существует, обновляем название
    if not created and product.name != name:
        product.name = name
        product.save()

    # Создаем или обновляем товар поставщика
    supplier_product, sp_created = SupplierProduct.objects.update_or_create(
        product=product,
        supplier=supplier,
        defaults={
            'price': price,
            'quantity': quantity,
            'is_active': True
        }
    )

    return {'action': 'created' if sp_created else 'updated'}

def _import_supplier_row(row):
    """Импорт одной строки поставщика"""
    username = row.get('username')
    email = row.get('email')
    phone = str(row.get('phone', ''))

    supplier, created = SupplierModel.objects.update_or_create(
        username=username,
        defaults={
            'email': email,
            'phone': phone,
            'user_type': 'supplier',
            'is_active': True
        }
    )

    return {'action': 'created' if created else 'updated'}

# ЗАДАЧИ ЭКСПОРТА

@shared_task(name='apps.import_export.tasks.do_export', queue='export')
def do_export(model_name, user_id, filters=None):
    """
    Асинхронный экспорт данных

        model_name: Название модели (products, suppliers)
        user_id: ID пользователя для уведомления
        filters: Словарь фильтров
    """
    User = get_user_model()

    try:
        # Получаем данные
        if model_name == 'products':
            queryset = SupplierProduct.objects.select_related('product', 'supplier')
            data = []
            for sp in queryset:
                data.append({
                    'ID': sp.id,
                    'Название товара': sp.product.name,
                    'Поставщик': sp.supplier.username,
                    'Цена': sp.price,
                    'Количество': sp.quantity,
                    'Активен': 'Да' if sp.is_active else 'Нет',
                })
            filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        elif model_name == 'suppliers':
            queryset = User.objects.filter(user_type='supplier')
            data = []
            for sup in queryset:
                data.append({
                    'ID': sup.id,
                    'Имя пользователя': sup.username,
                    'Email': sup.email,
                    'Телефон': sup.phone,
                    'Активен': 'Да' if sup.is_active else 'Нет',
                })
            filename = f"suppliers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        else:
            raise ValueError(f"Неизвестная модель: {model_name}")

        # Создаем CSV файл
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        # Сохраняем файл
        file_path = f"exports/{filename}"
        saved_path = default_storage.save(file_path, ContentFile(output.getvalue().encode('utf-8')))

        # Отправляем уведомление пользователю
        user = User.objects.get(id=user_id)
        send_email_task.delay(
            subject=f"📊 Экспорт {model_name} завершен",
            message=(
                f"Экспорт данных завершен!\n\n"
                f"📁 Файл: {filename}\n"
                f"📈 Экспортировано записей: {len(data)}\n"
                f"💾 Путь к файлу: {saved_path}"
            ),
            recipient_list=[user.email]
        )

        return {
            'status': 'success',
            'file_path': saved_path,
            'filename': filename,
            'count': len(data)
        }

    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        return {'status': 'error', 'message': str(e)}

# ПЕРИОДИЧЕСКИЕ ЗАДАЧИ

@shared_task(name='apps.products.tasks.check_low_stock')
def check_low_stock():
    """Проверка товаров с низким остатком"""
    threshold = 10
    low_stock_products = SupplierProduct.objects.filter(
        quantity__lte=threshold,
        quantity__gt=0,
        is_active=True
    ).select_related('product', 'supplier')

    out_of_stock = SupplierProduct.objects.filter(
        quantity=0,
        is_active=True
    ).select_related('product', 'supplier')

    # Отправляем уведомления поставщикам о низком остатке
    for product in low_stock_products:
        send_email_task.delay(
            subject=f"⚠️ Низкий остаток: {product.product.name}",
            message=(
                f"Уважаемый поставщик {product.supplier.username}!\n\n"
                f"Товар: {product.product.name}\n"
                f"SKU: {product.product.sku}\n"
                f"Остаток: {product.quantity} шт.\n"
                f"Порог: {threshold} шт.\n\n"
                f"Пожалуйста, пополните запасы."
            ),
            recipient_list=[product.supplier.email]
        )

    return {
        'status': 'success',
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock.count()
    }