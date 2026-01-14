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

