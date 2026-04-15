#!/bin/bash

# entrypoint.sh - скрипт для запуска Django приложения в Docker

echo "Waiting for database to be ready..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

echo "Waiting for Redis to be ready..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is ready!"

# Применяем миграции
echo "Applying database migrations..."
python manage.py migrate --noinput

# Собираем статику
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Создаем суперпользователя если его нет
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

echo "Starting server..."
exec "$@"
