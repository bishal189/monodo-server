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
    frozen_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=6.00,
        null=True,
        blank=True,
        help_text="Commission rate when user was frozen at submit (e.g. 6.00 for 6%). Used when they complete after topping up."
    )
    min_orders = models.IntegerField(default=0, help_text="Minimum number of orders required")
    start_continuous_orders_after = models.IntegerField(
        null=True,
        blank=True,
        help_text="Continuous orders start after this many (e.g. 8 means add at position 9, 10, ...). If null, uses max(0, min_orders - 10)."
    )
    price_min_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        help_text="Min % of balance for next product price (e.g. 30 for 30%%)"
    )
    price_max_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.00,
        help_text="Max % of balance for next product price (e.g. 70 for 70%%)"
    )
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
