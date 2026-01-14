from rest_framework import serializers
from .models import Level
from authentication.models import User


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = [
            'id',
            'level',
            'level_name',
            'required_points',
            'commission_rate',
            'min_orders',
            'benefits',
            'status',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_level(self, value):
        """Ensure level number is positive and unique"""
        if value < 1:
            raise serializers.ValidationError("Level must be a positive integer.")
        
        # Check uniqueness (excluding current instance if updating)
        queryset = Level.objects.filter(level=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A level with this number already exists.")
        return value
    
    def validate_required_points(self, value):
        """Ensure required points is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Required points must be non-negative.")
        return value
    
    def validate_commission_rate(self, value):
        """Ensure commission rate is between 0 and 100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Commission rate must be between 0 and 100.")
        return value
    
    def validate_min_orders(self, value):
        """Ensure min orders is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Minimum orders must be non-negative.")
        return value


class LevelCreateSerializer(LevelSerializer):
    """Serializer for creating levels"""
    pass


class LevelUpdateSerializer(LevelSerializer):
    """Serializer for updating levels"""
    level = serializers.IntegerField(required=False)
    level_name = serializers.CharField(required=False)
    required_points = serializers.IntegerField(required=False)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    min_orders = serializers.IntegerField(required=False)
    benefits = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Level.STATUS_CHOICES, required=False)


class AssignLevelSerializer(serializers.Serializer):
    """Serializer for assigning a level to a user"""
    user_id = serializers.IntegerField(required=True)
    level_id = serializers.IntegerField(required=True, allow_null=True)
    
    def validate_user_id(self, value):
        """Validate that the user exists"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")
        return value
    
    def validate_level_id(self, value):
        """Validate that the level exists if provided"""
        if value is not None:
            try:
                level = Level.objects.get(id=value)
                if level.status != 'ACTIVE':
                    raise serializers.ValidationError("Cannot assign an inactive level.")
            except Level.DoesNotExist:
                raise serializers.ValidationError("Level with this ID does not exist.")
        return value

