from django.db import models
from django.utils import timezone


class Level(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]
    
    level = models.IntegerField(unique=True, db_index=True, help_text="Level number")
    level_name = models.CharField(max_length=100, help_text="Name of the level")
    required_points = models.IntegerField(default=0, help_text="Points required to reach this level")
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Commission rate as percentage (e.g., 5.50 for 5.5%)"
    )
    min_orders = models.IntegerField(default=0, help_text="Minimum number of orders required")
    benefits = models.TextField(blank=True, null=True, help_text="Benefits description for this level")
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='ACTIVE',
        db_index=True,
        help_text="Status of the level"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'levels'
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
        ordering = ['level']
    
    def __str__(self):
        return f"Level {self.level}: {self.level_name}"
