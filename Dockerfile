FROM python:3.12-slim

WORKDIR /app

# Настройки pip для медленного интернета
ENV PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    PIP_NO_CACHE_DIR=0

COPY requirements.txt .

# Устанавливаем зависимости с несколькими попытками
RUN pip install --upgrade pip setuptools wheel && \
    pip install --timeout 600 --retries 10 -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
