from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=10, unique=True)
    image = models.ImageField(upload_to='user_images/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.mobile}"

class SMSLog(models.Model):
    mobile_number = models.CharField(max_length=15)
    ip_address = models.GenericIPAddressField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_success = models.BooleanField(default=True)
    response_data = models.TextField(blank=True, null=True)

    def __str__(self):
        status = "Success" if self.is_success else "Failed"
        return f"{self.mobile_number} - {status} at {self.sent_at}"
