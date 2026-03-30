"""
YAML загрузчик для импорта товаров от поставщиков.
"""

import yaml
import logging
from decimal import Decimal
from django.db import transaction
from apps.products.models import Category, Product, SupplierProduct
from apps.users.models import User
import os

logger = logging.getLogger(__name__)


class YAMLProductLoader:
    """
    Загрузчик товаров из YAML файла.
    """

    def __init__(self, file_path: str, supplier_id: int):
        self.file_path = file_path
        self.stats = {
            'created': 0,
            'updated': 0,
            'errors': [],
            'categories': 0,
        }


        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        try:
            self.supplier = User.objects.get(id=supplier_id, user_type='supplier')
        except User.DoesNotExist:
            raise ValueError(f"Поставщик с id {supplier_id} не найден")

    @transaction.atomic
    def load(self, update_existing: bool = True) -> dict:
        with open(self.file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        categories = self._process_categories(data.get('categories', []))
        self._process_offers(data.get('offers', []), categories, update_existing)

        return self.stats

    def _process_categories(self, categories_data):
        categories = {}
        for cat_data in categories_data:
            category_id = cat_data.get('id')
            name = cat_data.get('name')
            if not category_id or not name:
                continue

            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'is_active': True}
            )
            categories[category_id] = category
            if created:
                self.stats['categories'] += 1

        return categories

    def _process_offers(self, offers_data, categories, update_existing):
        for offer in offers_data:
            try:
                if not self._validate_offer(offer):
                    continue

                category = categories.get(offer.get('categoryId'))
                if not category:
                    continue

                product, created = self._get_or_create_product(offer, category)

                if created:
                    self.stats['created'] += 1

                self._update_supplier_product(product, offer, update_existing)

            except Exception as e:
                self.stats['errors'].append(str(e))

    def _validate_offer(self, offer):
        required = ['name', 'price', 'categoryId']
        for field in required:
            if field not in offer:
                return False
        try:
            price = Decimal(str(offer['price']))
            if price <= 0:
                return False
        except:
            return False
        return True

    def _get_or_create_product(self, offer, category):
        name = offer['name'].strip()
        product = Product.objects.filter(name__iexact=name).first()

        if product:
            product.description = offer.get('description', product.description)
            if offer.get('attributes'):
                product.attributes.update(offer['attributes'])
            product.save()
            return product, False

        product = Product.objects.create(
            name=name,
            category=category,
            description=offer.get('description', ''),
            attributes=offer.get('attributes', {}),
            is_active=True
        )
        return product, True

    def _update_supplier_product(self, product, offer, update_existing):
        price = Decimal(str(offer['price']))
        quantity = int(offer.get('quantity', 0))
        external_id = str(offer.get('id', ''))

        supplier_product = SupplierProduct.objects.filter(
            product=product,
            supplier=self.supplier
        ).first()

        if supplier_product:
            if not update_existing:
                return
            if price != supplier_product.price:
                supplier_product.old_price = supplier_product.price
            supplier_product.price = price
            supplier_product.quantity = quantity
            supplier_product.external_id = external_id
            supplier_product.is_active = quantity > 0
            supplier_product.save()
            self.stats['updated'] += 1
        else:
            SupplierProduct.objects.create(
                product=product,
                supplier=self.supplier,
                price=price,
                quantity=quantity,
                external_id=external_id,
                is_active=quantity > 0
            )
            self.stats['created'] += 1