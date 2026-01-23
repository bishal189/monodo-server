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
    withdrawal_account = models.ForeignKey(
        'WithdrawalAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        db_index=True,
        help_text="Withdrawal account used for this transaction (if withdrawal)"
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


class WithdrawalAccount(models.Model):
    CRYPTO_NETWORK_CHOICES = [
        ('TRC20', 'TRC20'),
        ('USDT', 'USDT'),
        ('BTC', 'BTC'),
        ('USDC', 'USDC'),
        ('ETH', 'ETH'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='withdrawal_accounts',
        db_index=True,
        help_text="User who owns this withdrawal account"
    )
    account_holder_name = models.CharField(
        max_length=255,
        help_text="Name of the account holder"
    )
    crypto_wallet_address = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Crypto wallet address"
    )
    crypto_network = models.CharField(
        max_length=20,
        choices=CRYPTO_NETWORK_CHOICES,
        help_text="Crypto network (TRC20, USDT, BTC, USDC, ETH)"
    )
    crypto_wallet_name = models.CharField(
        max_length=255,
        help_text="Name of the crypto wallet"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this account is active for withdrawals"
    )
    is_primary = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the primary withdrawal account"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'withdrawal_accounts'
        verbose_name = 'Withdrawal Account'
        verbose_name_plural = 'Withdrawal Accounts'
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.account_holder_name} - {self.crypto_wallet_name} - {self.crypto_network}"
    
    def clean(self):
        """Validate crypto network before saving"""
        from django.core.exceptions import ValidationError
        if self.crypto_network:
            valid_networks = [choice[0] for choice in self.CRYPTO_NETWORK_CHOICES]
            network_upper = self.crypto_network.upper().strip()
            if network_upper not in valid_networks:
                raise ValidationError({
                    'crypto_network': f"Invalid crypto network. Must be one of: {', '.join(valid_networks)}"
                })
            # Ensure uppercase
            self.crypto_network = network_upper
    
    def save(self, *args, **kwargs):
        # Validate and normalize crypto_network
        if self.crypto_network:
            valid_networks = [choice[0] for choice in self.CRYPTO_NETWORK_CHOICES]
            network_upper = self.crypto_network.upper().strip()
            if network_upper not in valid_networks:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'crypto_network': f"Invalid crypto network. Must be one of: {', '.join(valid_networks)}"
                })
            self.crypto_network = network_upper
        
        if self.is_primary:
            WithdrawalAccount.objects.filter(
                user=self.user,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)
