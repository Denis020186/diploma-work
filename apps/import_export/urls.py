"""
URL маршруты для импорта/экспорта
"""

from django.urls import path
from .views import ImportDataView, ExportDataView, TaskStatusView

urlpatterns = [
    path('import/', ImportDataView.as_view(), name='import-data'),
    path('export/', ExportDataView.as_view(), name='export-data'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
]