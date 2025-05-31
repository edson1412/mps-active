# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    RANK_CHOICES = [
        ('warder', 'Warder'),
        ('sergeant', 'Sergeant'),
        ('gaoler', 'Gaoler'),
        ('inspector', 'Inspector'),
    ]
    
    rank = models.CharField(max_length=20, choices=RANK_CHOICES)
    prison_station = models.ForeignKey(
        'prison.PrisonStation',  # Use string reference instead of direct import
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    must_change_password = models.BooleanField(default=True)
    
    def __str__(self):
        station_name = self.prison_station.name if self.prison_station else 'No station'
        return f"{self.get_full_name()} ({station_name})"