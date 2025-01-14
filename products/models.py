from PIL import Image
from PIL.Image import Resampling
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    image = models.ImageField(upload_to='category_images/')



    def clean(self):
        if self.image:
            if self.image.file.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValidationError("Максимальный размер файла 5MB")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.image:
            with Image.open(self.image.path) as img:
                # Convert to RGB if image is in RGBA mode
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Resize if larger than 800x800
                if img.height > 800 or img.width > 800:
                    output_size = (800, 800)
                    img.thumbnail(output_size, Resampling.LANCZOS)  # Changed this line

                # Save with optimization
                img.save(self.image.path, 'JPEG', quality=70, optimize=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # This will be used for category detail pages
        return reverse('products:category-detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # This will be used for product detail pages
        return reverse('products:product-detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')

    def clean(self):
        if self.image:
            if self.image.file.size > 5 * 1024 * 1024:
                raise ValidationError("Максимальный размер файла 5MB")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.image:
            with Image.open(self.image.path) as img:
                # Convert to RGB if image is in RGBA mode
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Resize if larger than 1200x1200
                if img.height > 1200 or img.width > 1200:
                    output_size = (1200, 1200)
                    img.thumbnail(output_size, Resampling.LANCZOS)

                # Save with optimization
                img.save(self.image.path, 'JPEG', quality=75, optimize=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        verbose_name = 'Изображение продукта'
        verbose_name_plural = 'Изображения продуктов'
