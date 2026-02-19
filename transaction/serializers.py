from rest_framework import serializers
from .models import Transaction, WithdrawalAccount
from authentication.models import User


class TransactionSerializer(serializers.ModelSerializer):
    member_account_email = serializers.EmailField(source='member_account.email', read_only=True)
    member_account_username = serializers.CharField(source='member_account.username', read_only=True)
    withdrawal_account_details = serializers.SerializerMethodField()
    
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
            'withdrawal_account',
            'withdrawal_account_details',
            'created_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at']
    
    def get_withdrawal_account_details(self, obj):
        if obj.withdrawal_account:
            serializer = WithdrawalAccountSerializer(obj.withdrawal_account)
            return serializer.data
        return None
    
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
    withdrawal_account_id = serializers.IntegerField(required=False, allow_null=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    
    def validate_withdrawal_account_id(self, value):
        """Validate withdrawal account exists and belongs to user"""
        if value is None:
            return value
        
        user = self.context.get('user')
        if not user:
            return value
        
        from .models import WithdrawalAccount
        try:
            withdrawal_account = WithdrawalAccount.objects.get(id=value, user=user)
            if not withdrawal_account.is_active:
                raise serializers.ValidationError("The selected withdrawal account is not active.")
            return value
        except WithdrawalAccount.DoesNotExist:
            raise serializers.ValidationError("Withdrawal account not found or does not belong to you.")
    
    def validate(self, attrs):
        """Validate withdraw password and sufficient balance"""
        user = self.context['user']
        amount = attrs.get('amount')
        withdraw_password = attrs.get('withdraw_password')
        withdrawal_account_id = attrs.get('withdrawal_account_id')
        
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
        
        from .models import WithdrawalAccount
        if withdrawal_account_id is None:
            primary_account = WithdrawalAccount.objects.filter(user=user, is_primary=True, is_active=True).first()
            if not primary_account:
                active_accounts = WithdrawalAccount.objects.filter(user=user, is_active=True).first()
                if not active_accounts:
                    raise serializers.ValidationError({
                        'withdrawal_account_id': 'Please add a withdrawal account first or specify a withdrawal account.'
                    })
                attrs['withdrawal_account_id'] = active_accounts.id
            else:
                attrs['withdrawal_account_id'] = primary_account.id
        
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


class WithdrawalAccountSerializer(serializers.ModelSerializer):
    masked_wallet_address = serializers.SerializerMethodField()
    
    class Meta:
        model = WithdrawalAccount
        fields = [
            'id',
            'account_holder_name',
            'crypto_wallet_address',
            'masked_wallet_address',
            'crypto_network',
            'crypto_wallet_name',
            'is_active',
            'is_primary',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'masked_wallet_address', 'created_at', 'updated_at']
    
    def get_masked_wallet_address(self, obj):
        if obj.crypto_wallet_address:
            if len(obj.crypto_wallet_address) > 8:
                return obj.crypto_wallet_address[:6] + '...' + obj.crypto_wallet_address[-4:]
            return '*' * len(obj.crypto_wallet_address)
        return None


class WithdrawalAccountCreateSerializer(serializers.ModelSerializer):
    crypto_network = serializers.ChoiceField(
        choices=WithdrawalAccount.CRYPTO_NETWORK_CHOICES,
        help_text="Crypto network: TRC20, USDT, BTC, USDC, or ETH"
    )
    
    class Meta:
        model = WithdrawalAccount
        fields = [
            'account_holder_name',
            'crypto_wallet_address',
            'crypto_network',
            'crypto_wallet_name',
            'is_primary'
        ]
    
    def validate_crypto_wallet_address(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Crypto wallet address is required.")
        return value.strip()
    
    def validate_account_holder_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Account holder name is required.")
        return value.strip()
    
    def validate_crypto_wallet_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Crypto wallet name is required.")
        return value.strip()
    
    def validate_crypto_network(self, value):
        if not value:
            raise serializers.ValidationError("Crypto network is required.")
        # Convert to uppercase to handle case-insensitive input
        value = value.upper().strip()
        valid_networks = [choice[0] for choice in WithdrawalAccount.CRYPTO_NETWORK_CHOICES]
        if value not in valid_networks:
            raise serializers.ValidationError(
                f"Invalid crypto network '{value}'. Must be one of: {', '.join(valid_networks)}"
            )
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class WithdrawalAccountUpdateSerializer(serializers.ModelSerializer):
    crypto_network = serializers.ChoiceField(
        choices=WithdrawalAccount.CRYPTO_NETWORK_CHOICES,
        required=False,
        help_text="Crypto network: TRC20, USDT, BTC, USDC, or ETH"
    )
    
    class Meta:
        model = WithdrawalAccount
        fields = [
            'account_holder_name',
            'crypto_wallet_address',
            'crypto_network',
            'crypto_wallet_name',
            'is_active',
            'is_primary'
        ]
    
    def validate_crypto_wallet_address(self, value):
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Crypto wallet address cannot be empty.")
        return value.strip() if value else value
    
    def validate_account_holder_name(self, value):
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Account holder name cannot be empty.")
        return value.strip() if value else value
    
    def validate_crypto_wallet_name(self, value):
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Crypto wallet name cannot be empty.")
        return value.strip() if value else value
    
    def validate_crypto_network(self, value):
        if value:
            # Convert to uppercase to handle case-insensitive input
            value = value.upper().strip()
            valid_networks = [choice[0] for choice in WithdrawalAccount.CRYPTO_NETWORK_CHOICES]
            if value not in valid_networks:
                raise serializers.ValidationError(
                    f"Invalid crypto network '{value}'. Must be one of: {', '.join(valid_networks)}"
                )
        return value


class WithdrawalAccountWalletModalSerializer(serializers.ModelSerializer):
    wallet_name = serializers.CharField(source='crypto_wallet_name', read_only=True)
    wallet_address = serializers.CharField(source='crypto_wallet_address', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True, default='')
    currency = serializers.SerializerMethodField()
    network_type = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalAccount
        fields = ['wallet_name', 'wallet_address', 'phone_number', 'currency', 'network_type']

    def get_currency(self, obj):
        raw = (obj.crypto_network or '').upper()
        return 'USDT' if raw == 'TRC20' else (raw if raw in ('USDT', 'USDC', 'ETH', 'BTC') else 'USDT')

    def get_network_type(self, obj):
        raw = (obj.crypto_network or '').upper()
        return 'TRC 20' if raw == 'TRC20' else raw


class WithdrawalAccountWalletModalUpdateSerializer(serializers.Serializer):
    wallet_name = serializers.CharField(required=False, allow_blank=False)
    wallet_address = serializers.CharField(required=False, allow_blank=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    currency = serializers.ChoiceField(
        choices=[('USDT', 'USDT'), ('USDC', 'USDC'), ('ETH', 'ETH'), ('BTC', 'BTC')],
        required=False
    )
    network_type = serializers.CharField(required=False)

    _valid_networks = [c[0] for c in WithdrawalAccount.CRYPTO_NETWORK_CHOICES]

    def validate_network_type(self, value):
        if not value:
            return value
        v = value.upper().strip().replace(' ', '')
        if v == 'TRC20':
            return 'TRC20'
        if v in ('ERC20', 'ERC 20'):
            cur = self.initial_data.get('currency', '').upper().strip()
            return 'USDC' if cur == 'USDC' else 'ETH'
        if v in self._valid_networks:
            return v
        raise serializers.ValidationError(
            "Must be one of: TRC 20, TRC20, ERC 20, USDT, USDC, ETH, BTC"
        )

    def update(self, instance, validated_data):
        if 'wallet_name' in validated_data:
            instance.crypto_wallet_name = validated_data['wallet_name'].strip()
        if 'wallet_address' in validated_data:
            instance.crypto_wallet_address = validated_data['wallet_address'].strip()
        if 'phone_number' in validated_data:
            instance.user.phone_number = validated_data.get('phone_number') or ''
            instance.user.save(update_fields=['phone_number'])
        if 'network_type' in validated_data and validated_data['network_type']:
            instance.crypto_network = validated_data['network_type']
        elif 'currency' in validated_data and validated_data['currency']:
            instance.crypto_network = validated_data['currency']
        instance.save()
        return instance
