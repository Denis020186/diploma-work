"""
Management команда для импорта товаров из YAML файла.
"""

from django.core.management.base import BaseCommand, CommandError
from apps.import_export.yaml_loader import YAMLProductLoader
from apps.users.models import User


class Command(BaseCommand):
    help = 'Импорт товаров из YAML файла'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)
        parser.add_argument('supplier_id', type=int)

    def handle(self, *args, **options):
        file_path = options['file_path']
        supplier_id = options['supplier_id']

        try:
            supplier = User.objects.get(id=supplier_id, user_type='supplier')
            self.stdout.write(f"Поставщик: {supplier.username}")
        except User.DoesNotExist:
            raise CommandError(f'Поставщик с ID {supplier_id} не найден')

        loader = YAMLProductLoader(file_path, supplier_id)
        stats = loader.load()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('РЕЗУЛЬТАТЫ ИМПОРТА'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f"Создано товаров: {stats['created']}")
        self.stdout.write(f"Обновлено товаров: {stats['updated']}")
        self.stdout.write(f"Создано категорий: {stats['categories']}")

        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"\nОшибок: {len(stats['errors'])}"))
            for error in stats['errors']:
                self.stdout.write(self.style.ERROR(f"  - {error}"))