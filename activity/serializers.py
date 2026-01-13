from rest_framework import serializers
from .models import LoginActivity


class LoginActivitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    ip_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = LoginActivity
        fields = [
            'id',
            'user',
            'user_email',
            'user_username',
            'ip_address',
            'browser',
            'operating_system',
            'device_type',
            'login_time'
        ]
        read_only_fields = ['id', 'login_time']

