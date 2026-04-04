"""
API views для импорта/экспорта данных
"""

import base64
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from celery.result import AsyncResult
from .tasks import do_import, do_export


class ImportDataView(APIView):
    """
    API для импорта данных (запуск Celery задачи)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        """
        Запуск импорта данных из файла

        Ожидает:
            - file: загруженный файл (CSV, Excel)
            - model_name: products, suppliers
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Файл не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        model_name = request.data.get('model_name')

        if not model_name:
            return Response(
                {'error': 'Не указана модель для импорта'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Читаем файл и кодируем в base64
        file_content = base64.b64encode(uploaded_file.read()).decode('utf-8')

        # Запускаем Celery задачу
        task = do_import.delay(
            file_content=file_content,
            filename=uploaded_file.name,
            model_name=model_name,
            user_id=request.user.id
        )

        return Response({
            'task_id': task.id,
            'status': 'started',
            'message': f'Импорт {model_name} запущен',
            'check_status_url': f'/api/v1/import-export/task-status/{task.id}/'
        }, status=status.HTTP_202_ACCEPTED)

class ExportDataView(APIView):
    """
    API для экспорта данных (запуск Celery задачи)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        """
        Запуск экспорта данных
        """
        model_name = request.data.get('model_name')

        if not model_name:
            return Response(
                {'error': 'Не указана модель для экспорта'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Запускаем Celery задачу
        task = do_export.delay(
            model_name=model_name,
            user_id=request.user.id,
            filters=request.data.get('filters', {})
        )

        return Response({
            'task_id': task.id,
            'status': 'started',
            'message': f'Экспорт {model_name} запущен',
            'check_status_url': f'/api/v1/import-export/task-status/{task.id}/'
        }, status=status.HTTP_202_ACCEPTED)

class TaskStatusView(APIView):
    """
    API для проверки статуса Celery задачи
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, task_id):
        """Получение статуса задачи по ID"""
        task = AsyncResult(task_id)

        response = {
            'task_id': task_id,
            'status': task.status,
            'ready': task.ready(),
        }

        if task.ready():
            if task.successful():
                response['result'] = task.result
            else:
                response['error'] = str(task.info)
        else:
            if task.info:
                response['progress'] = task.info

        return Response(response)