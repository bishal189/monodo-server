from django.db import models
from django.utils import timezone
from authentication.models import User
import secrets
import string


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
        ('REFUND', 'Refund'),
        ('COMMISSION', 'Commission'),
        ('BONUS', 'Bonus'),
    ]
    
    REMARK_TYPE_CHOICES = [
        ('PAYMENT', 'Payment'),
        ('REFUND', 'Refund'),
        ('COMMISSION', 'Commission'),
        ('BONUS', 'Bonus'),
        ('PENALTY', 'Penalty'),
        ('ADJUSTMENT', 'Adjustment'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    transaction_id = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Unique transaction identifier"
    )
    member_account = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_index=True,
        help_text="User account associated with this transaction"
    )
    type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        db_index=True,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    remark_type = models.CharField(
        max_length=20,
        choices=REMARK_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Type of remark"
    )
    remark = models.TextField(
        blank=True,
        null=True,
        help_text="Additional remarks or description"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text="Transaction status"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['member_account', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.member_account.email} - {self.type}"
    
    def save(self, *args, **kwargs):
        """Generate unique transaction ID if not provided"""
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_transaction_id():
        """Generate a unique transaction ID"""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            # Format: TXN + 12 random characters
            transaction_id = 'TXN' + ''.join(secrets.choice(alphabet) for _ in range(12))
            if not Transaction.objects.filter(transaction_id=transaction_id).exists():
                return transaction_id
