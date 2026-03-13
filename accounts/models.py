from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.mobile}"
