from django.db import models
from django.conf import settings


class LoginActivity(models.Model):
    DEVICE_TYPE_CHOICES = [
        ('DESKTOP', 'Desktop'),
        ('MOBILE', 'Mobile'),
        ('TABLET', 'Tablet'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_activities')
    ip_address = models.GenericIPAddressField()
    browser = models.CharField(max_length=100)
    operating_system = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES, default='OTHER')
    login_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'login_activities'
        verbose_name = 'Login Activity'
        verbose_name_plural = 'Login Activities'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['-login_time']),
            models.Index(fields=['user', '-login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
