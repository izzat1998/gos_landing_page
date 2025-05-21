import uuid

from django.db import models
from django.db.models.deletion import ProtectedError

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
    visit_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = "Скан QR-кода"
        verbose_name_plural = "Сканы QR-кодов"


class PhoneClick(models.Model):
    scan = models.ForeignKey(QRCodeScan, on_delete=models.CASCADE, related_name='phone_clicks')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Клик по номеру телефона"
        verbose_name_plural = "Клики по номерам телефонов"
