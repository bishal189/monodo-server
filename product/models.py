from django.db import models
from django.utils import timezone


class Product(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('OUT_OF_STOCK', 'Out of Stock'),
    ]
    
    image = models.ImageField(upload_to='products/', blank=True, null=True, help_text="Product image")
    title = models.CharField(max_length=200, db_index=True, help_text="Product title")
    description = models.TextField(blank=True, null=True, help_text="Product description")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Product price"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='ACTIVE',
        db_index=True,
        help_text="Product status"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
