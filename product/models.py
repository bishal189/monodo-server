from django.db import models
from django.utils import timezone
from authentication.models import User


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
    levels = models.ManyToManyField(
        'level.Level',
        related_name='products',
        blank=True,
        help_text="Levels this product is assigned to"
    )
    position = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Display position/order for the product (lower number = higher position)"
    )
    use_actual_price = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If True, always use product price (no 30-70%% agreed price). Set when inserted at position from frontend."
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['position', '-created_at']
    
    def __str__(self):
        return self.title


class ProductReview(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        db_index=True,
        help_text="User who submitted the review"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        db_index=True,
        help_text="Product being reviewed"
    )
    review_text = models.TextField(blank=True, null=True, help_text="Review content")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text="Review status"
    )
    commission_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Commission earned from this review"
    )
    agreed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price agreed for this user (30-70%% of balance when assigned); used for commission"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When review was completed")
    
    class Meta:
        db_table = 'product_reviews'
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'
        ordering = ['-created_at']
        unique_together = ['user', 'product']  # User can only review each product once
    
    def __str__(self):
        return f"{self.user.username} - {self.product.title} - {self.status}"
