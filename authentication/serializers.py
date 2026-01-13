from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
import secrets
import string
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    login_password = serializers.CharField(write_only=True, required=True)
    confirm_login_password = serializers.CharField(write_only=True, required=True)
    confirm_withdraw_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username',
            'phone_number',
            'email',
            'login_password',
            'confirm_login_password',
            'withdraw_password',
            'confirm_withdraw_password',
            'invitation_code'
        ]
        extra_kwargs = {
            'withdraw_password': {'write_only': True, 'required': False, 'allow_blank': True},
            'email': {'required': True},
            'invitation_code': {'required': False, 'allow_blank': True},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    
    def validate(self, attrs):
        login_password = attrs.get('login_password')
        confirm_login_password = attrs.get('confirm_login_password')
        withdraw_password = attrs.get('withdraw_password')
        confirm_withdraw_password = attrs.get('confirm_withdraw_password')
        
        if login_password != confirm_login_password:
            raise serializers.ValidationError({
                'confirm_login_password': "Login passwords do not match."
            })
        
        try:
            validate_password(login_password)
        except Exception as e:
            raise serializers.ValidationError({
                'login_password': list(e.messages)
            })
        
        if withdraw_password:
            if withdraw_password != confirm_withdraw_password:
                raise serializers.ValidationError({
                    'confirm_withdraw_password': "Withdraw passwords do not match."
                })
            if len(withdraw_password) < 4:
                raise serializers.ValidationError({
                    'withdraw_password': "Withdraw password must be at least 4 characters long."
                })
        
        return attrs
    
    def generate_unique_invitation_code(self):
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not User.objects.filter(invitation_code=code).exists():
                return code
    
    def create(self, validated_data):
        validated_data.pop('confirm_login_password')
        validated_data.pop('confirm_withdraw_password', None)
        login_password = validated_data.pop('login_password')
        withdraw_password = validated_data.pop('withdraw_password', None)
        invitation_code = validated_data.pop('invitation_code', None)
        
        if not invitation_code:
            invitation_code = self.generate_unique_invitation_code()
        else:
            if User.objects.filter(invitation_code=invitation_code).exists():
                raise serializers.ValidationError({
                    'invitation_code': 'This invitation code is already taken.'
                })
        
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            phone_number=validated_data['phone_number'],
            login_password=login_password,
            withdraw_password=withdraw_password,
            invitation_code=invitation_code,
            role='USER'
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                if user.check_password(password) and user.is_active:
                    attrs['user'] = user
                    return attrs
                elif not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                else:
                    raise serializers.ValidationError('Invalid email or password.')
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid email or password.')
        
        raise serializers.ValidationError('Email and password are required.')


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'phone_number',
            'invitation_code',
            'role',
            'date_joined',
            'last_login',
            'is_active'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'role']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'phone_number', 'email']
    
    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        user = self.instance
        if User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_phone_number(self, value):
        user = self.instance
        if User.objects.filter(phone_number=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
