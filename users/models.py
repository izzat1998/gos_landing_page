# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=20)
    telegram_id = models.CharField(max_length=20)

    def __str__(self):
        return self.username
