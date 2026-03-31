from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.products.models import Category, Product, SupplierProduct
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает тестовые данные для API'

    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых данных...')

        # Создаем категории
        categories = []
        for cat_name in ['Электроника', 'Одежда', 'Книги', 'Дом и сад']:
            cat, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'is_active': True}
            )
            categories.append(cat)
            self.stdout.write(f'✓ Категория: {cat_name}')

        # Создаем поставщика (supplier)
        supplier, created = User.objects.get_or_create(
            username='supplier1',
            defaults={
                'email': 'supplier1@example.com',
                'user_type': 'supplier',
                'phone': '+79991234567',
                'company_name': 'ООО "ТехноПоставка"'
            }
        )
        if created:
            supplier.set_password('supplier123')
            supplier.save()
            self.stdout.write(f'✓ Поставщик: {supplier.username}')

        # Создаем покупателя (buyer)
        buyer, created = User.objects.get_or_create(
            username='buyer1',
            defaults={
                'email': 'buyer1@example.com',
                'user_type': 'buyer',
                'phone': '+79997654321',
            }
        )
        if created:
            buyer.set_password('buyer123')
            buyer.save()
            self.stdout.write(f'✓ Покупатель: {buyer.username}')

        # Создаем товары
        products_data = [
            {'name': 'Смартфон X100', 'category': 'Электроника', 'brand': 'TechBrand', 'sku': 'PHONE-001',
             'price': 29999, 'quantity': 10},
            {'name': 'Ноутбук Pro 15', 'category': 'Электроника', 'brand': 'TechBrand', 'sku': 'LAPTOP-001',
             'price': 69999, 'quantity': 5},
            {'name': 'Наушники Wireless', 'category': 'Электроника', 'brand': 'AudioTech', 'sku': 'AUDIO-001',
             'price': 4999, 'quantity': 20},
            {'name': 'Футболка хлопок', 'category': 'Одежда', 'brand': 'FashionStyle', 'sku': 'CLOTH-001', 'price': 999,
             'quantity': 50},
            {'name': 'Джинсы классические', 'category': 'Одежда', 'brand': 'FashionStyle', 'sku': 'CLOTH-002',
             'price': 2499, 'quantity': 30},
            {'name': 'Python программирование', 'category': 'Книги', 'brand': 'Издательство', 'sku': 'BOOK-001',
             'price': 899, 'quantity': 15},
            {'name': 'Django 4 для начинающих', 'category': 'Книги', 'brand': 'Издательство', 'sku': 'BOOK-002',
             'price': 1299, 'quantity': 10},
        ]

        for prod_data in products_data:
            category = Category.objects.get(name=prod_data['category'])
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'category': category,
                    'brand': prod_data['brand'],
                    'sku': prod_data['sku'],
                    'description': f'Описание товара {prod_data["name"]}',
                    'attributes': {'color': 'черный', 'material': 'пластик'},
                    'is_active': True
                }
            )

            # Создаем товар поставщика
            supplier_product, created = SupplierProduct.objects.get_or_create(
                product=product,
                supplier=supplier,
                defaults={
                    'price': Decimal(str(prod_data['price'])),
                    'quantity': prod_data['quantity'],
                    'is_active': True
                }
            )
            self.stdout.write(f'✓ Товар: {product.name} - {prod_data["price"]} руб.')

        self.stdout.write(self.style.SUCCESS('✅ Тестовые данные успешно созданы!'))