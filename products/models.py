from PIL import Image
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    image = models.ImageField(upload_to='category_images/')

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
                if img.height > 1200 or img.width > 1200:
                    img.thumbnail((1200, 1200))
                    img.save(self.image.path)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        verbose_name = 'Изображение продукта'
        verbose_name_plural = 'Изображения продуктов'
