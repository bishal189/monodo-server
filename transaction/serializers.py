from rest_framework import serializers
from .models import Transaction
from authentication.models import User


class TransactionSerializer(serializers.ModelSerializer):
    member_account_email = serializers.EmailField(source='member_account.email', read_only=True)
    member_account_username = serializers.CharField(source='member_account.username', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'member_account',
            'member_account_email',
            'member_account_username',
            'type',
            'amount',
            'remark_type',
            'remark',
            'status',
            'created_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at']
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class TransactionCreateSerializer(TransactionSerializer):
    """Serializer for creating transactions"""
    transaction_id = serializers.CharField(required=False, max_length=50)
    member_account = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    type = serializers.ChoiceField(choices=Transaction.TRANSACTION_TYPE_CHOICES, required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    remark_type = serializers.ChoiceField(choices=Transaction.REMARK_TYPE_CHOICES, required=False, allow_null=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(choices=Transaction.STATUS_CHOICES, required=False, default='PENDING')


class TransactionUpdateSerializer(TransactionSerializer):
    """Serializer for updating transactions"""
    transaction_id = serializers.CharField(read_only=True)
    member_account = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    type = serializers.ChoiceField(choices=Transaction.TRANSACTION_TYPE_CHOICES, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    remark_type = serializers.ChoiceField(choices=Transaction.REMARK_TYPE_CHOICES, required=False, allow_null=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(choices=Transaction.STATUS_CHOICES, required=False)


class DepositSerializer(serializers.Serializer):
    """Serializer for deposit transactions"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class WithdrawSerializer(serializers.Serializer):
    """Serializer for withdrawal transactions"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    withdraw_password = serializers.CharField(required=True, write_only=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    
    def validate(self, attrs):
        """Validate withdraw password and sufficient balance"""
        user = self.context['user']
        amount = attrs.get('amount')
        withdraw_password = attrs.get('withdraw_password')
        
        if not user.withdraw_password:
            raise serializers.ValidationError({
                'withdraw_password': 'Withdraw password is not set. Please set it first.'
            })
        
        if user.withdraw_password != withdraw_password:
            raise serializers.ValidationError({
                'withdraw_password': 'Invalid withdraw password.'
            })
        
        if user.balance < amount:
            raise serializers.ValidationError({
                'amount': f'Insufficient balance. Available balance: {user.balance}'
            })
        
        return attrs


class BalanceAdjustmentSerializer(serializers.Serializer):
    """Serializer for admin/agent to add/subtract balance (debit/credit)"""
    BALANCE_TYPE_CHOICES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    
    member_account = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=True,
        help_text="User account to adjust balance for"
    )
    type = serializers.ChoiceField(
        choices=BALANCE_TYPE_CHOICES,
        required=True,
        help_text="CREDIT to add balance, DEBIT to subtract balance"
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        help_text="Amount to adjust"
    )
    remark_type = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=20,
        help_text="Type of remark (any text allowed)"
    )
    remark = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Additional remarks or description"
    )
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        member_account = attrs.get('member_account')
        balance_type = attrs.get('type')
        amount = attrs.get('amount')
        
        if balance_type == 'DEBIT':
            if member_account.balance < amount:
                if not attrs.get('remark'):
                    attrs['remark'] = f'Balance adjustment: Original balance was {member_account.balance}. This may result in negative balance.'
        
        return attrs

