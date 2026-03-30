from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ImportExportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.import_export'
    verbose_name = _('Импорт и экспорт')