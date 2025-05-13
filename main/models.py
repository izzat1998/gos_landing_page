from django.db import models

# Create your models here.

class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

class QRCodeScan(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='scans')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Скан QR-кода'
        verbose_name_plural = 'Сканы QR-кодов'
