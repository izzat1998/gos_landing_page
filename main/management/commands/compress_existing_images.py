# products/management/commands/compress_existing_images.py
from PIL.Image import Resampling
from django.core.management.base import BaseCommand
from PIL import Image
from products.models import Category, ProductImage


class Command(BaseCommand):
    help = 'Compress existing images'

    def handle(self, *args, **kwargs):
        # Compress category images
        categories = Category.objects.all()
        for category in categories:
            if category.image:
                try:
                    with Image.open(category.image.path) as img:
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')

                        if img.height > 800 or img.width > 800:
                            output_size = (800, 800)
                            img.thumbnail(output_size, Resampling.LANCZOS)

                        img.save(category.image.path, 'JPEG', quality=70, optimize=True)
                        self.stdout.write(self.style.SUCCESS(f'Compressed category image: {category.name}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error with category {category.name}: {str(e)}'))

        # Compress product images
        product_images = ProductImage.objects.all()
        for prod_image in product_images:
            if prod_image.image:
                try:
                    with Image.open(prod_image.image.path) as img:
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')

                        if img.height > 1200 or img.width > 1200:
                            output_size = (1200, 1200)
                            img.thumbnail(output_size, Resampling.LANCZOS)

                        img.save(prod_image.image.path, 'JPEG', quality=75, optimize=True)
                        self.stdout.write(self.style.SUCCESS(f'Compressed product image: {prod_image.product.name}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error with product image {prod_image.product.name}: {str(e)}'))