# app_name/management/commands/generate_dummy_data.py
from django.core.management.base import BaseCommand
from django.core.files import File
from pathlib import Path
from faker import Faker
from decimal import Decimal
import random
import os
from products.models import Category, Product, ProductImage

class Command(BaseCommand):
    help = 'Generate dummy furniture data for the shop'

    def add_arguments(self, parser):
        parser.add_argument('--images-dir', type=str, required=True)
        parser.add_argument('--products-per-category', type=int, default=20)
        parser.add_argument('--images-per-product', type=int, default=3)

    def handle(self, *args, **options):
        fake = Faker()
        images_dir = Path(options['images_dir'])

        if not images_dir.exists() or not images_dir.is_dir():
            self.stdout.write(self.style.ERROR(f'Directory {images_dir} does not exist'))
            return

        image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png')) + list(images_dir.glob('*.jpeg'))
        if not image_files:
            self.stdout.write(self.style.ERROR('No image files found in directory'))
            return

        # Predefined furniture categories
        furniture_categories = [
            {
                'name': 'Гостиная',
                'description': 'Мебель для гостиной комнаты: диваны, кресла, журнальные столики, тумбы под ТВ',
                'products': ['Диван угловой', 'Кресло-реклайнер', 'Журнальный столик', 'Тумба ТВ']
            },
            {
                'name': 'Спальня',
                'description': 'Мебель для спальни: кровати, шкафы, комоды, прикроватные тумбочки',
                'products': ['Кровать двуспальная', 'Шкаф-купе', 'Комод', 'Тумба прикроватная']
            },
            {
                'name': 'Кухня',
                'description': 'Кухонная мебель: столы, стулья, кухонные гарнитуры',
                'products': ['Стол обеденный', 'Стул кухонный', 'Кухонный гарнитур', 'Барный стул']
            },
            {
                'name': 'Офис',
                'description': 'Офисная мебель: столы, кресла, шкафы для документов',
                'products': ['Стол рабочий', 'Кресло офисное', 'Шкаф для документов', 'Тумба подкатная']
            },
            {
                'name': 'Детская',
                'description': 'Мебель для детской комнаты: кровати, столы, шкафы',
                'products': ['Кровать детская', 'Стол письменный', 'Шкаф детский', 'Комод детский']
            }
        ]

        # Generate categories and their products
        for cat_data in furniture_categories:
            category = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description']
            )
            with open(random.choice(image_files), 'rb') as img_file:
                category.image.save(
                    os.path.basename(img_file.name),
                    File(img_file),
                    save=True
                )
            
            # Generate products for each category
            for product_name in cat_data['products']:
                product = Product.objects.create(
                    name=product_name,
                    description=fake.paragraph(nb_sentences=5),
                    price=Decimal(random.uniform(1000, 100000)).quantize(Decimal('0.01')),
                    category=category
                )
                
                # Generate product images
                for _ in range(random.randint(1, options['images_per_product'])):
                    product_image = ProductImage(product=product)
                    with open(random.choice(image_files), 'rb') as img_file:
                        product_image.image.save(
                            os.path.basename(img_file.name),
                            File(img_file),
                            save=True
                        )
                
                self.stdout.write(f'Created product: {product.name} in {category.name}')

        self.stdout.write(self.style.SUCCESS('Successfully generated furniture data'))