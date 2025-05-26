import uuid

from django.db import models
from django.db.models.deletion import ProtectedError
from django.utils.text import slugify

from users.models import CustomUser

# Create your models here.


class LocationQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise ProtectedError("Удаление локаций запрещено.", self)


class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ManyToManyField(CustomUser, related_name="locations")

    objects = LocationQuerySet.as_manager()

    def delete(self, *args, **kwargs):
        raise ProtectedError("Удаление локаций запрещено.", self)

    def __str__(self):
        return self.name


class QRCodeScan(models.Model):
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="scans"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    visit_id = models.UUIDField(default=uuid.uuid4, editable=False, null=True)

    class Meta:
        verbose_name = "Скан QR-кода"
        verbose_name_plural = "Сканы QR-кодов"


class PhoneClick(models.Model):
    scan = models.ForeignKey(
        QRCodeScan, on_delete=models.CASCADE, related_name="phone_clicks"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Клик по номеру телефона"
        verbose_name_plural = "Клики по номерам телефонов"


class FurnitureCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    slug = models.SlugField(
        max_length=100, unique=True, verbose_name="URL-идентификатор"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(
        upload_to="categories/", blank=True, null=True, verbose_name="Изображение"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Категория мебели"
        verbose_name_plural = "Категории мебели"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FurnitureItem(models.Model):
    category = models.ForeignKey(
        FurnitureCategory,
        on_delete=models.CASCADE,
        related_name="furniture_items",
        verbose_name="Категория",
    )
    name = models.CharField(max_length=200, verbose_name="Название")
    slug = models.SlugField(
        max_length=200, unique=True, verbose_name="URL-идентификатор"
    )
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Цена"
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Цена со скидкой",
    )
    main_image = models.ImageField(
        upload_to="furniture/", verbose_name="Основное изображение"
    )
    is_featured = models.BooleanField(default=False, verbose_name="Рекомендуемый товар")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    dimensions = models.CharField(max_length=100, blank=True, verbose_name="Размеры")
    materials = models.CharField(max_length=200, blank=True, verbose_name="Материалы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Мебель"
        verbose_name_plural = "Мебель"
        ordering = ["-is_featured", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FurnitureImage(models.Model):
    furniture = models.ForeignKey(
        FurnitureItem,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Мебель",
    )
    image = models.ImageField(
        upload_to="furniture_gallery/", verbose_name="Изображение"
    )
    alt_text = models.CharField(
        max_length=100, blank=True, verbose_name="Альтернативный текст"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения")

    class Meta:
        verbose_name = "Изображение мебели"
        verbose_name_plural = "Изображения мебели"
        ordering = ["order"]

    def __str__(self):
        return f"Изображение для {self.furniture.name}"
