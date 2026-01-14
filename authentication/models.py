from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, username, phone_number, login_password, withdraw_password=None, invitation_code=None, role='USER', **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            phone_number=phone_number,
            invitation_code=invitation_code,
            role=role,
            **extra_fields
        )
        user.set_password(login_password)
        if withdraw_password:
            user.withdraw_password = withdraw_password
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        if password is None:
            raise ValueError('Superuser must have a password.')
        
        return self.create_user(email, username, phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('AGENT', 'Agent'),
        ('USER', 'User'),
    ]
    
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    withdraw_password = models.CharField(max_length=128, blank=True, null=True)
    invitation_code = models.CharField(max_length=50, unique=True, blank=True, null=True, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER', db_index=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')
    level = models.ForeignKey('level.Level', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email
    
    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.is_superuser
    
    @property
    def is_agent(self):
        return self.role == 'AGENT'
    
    @property
    def is_normal_user(self):
        return self.role == 'USER'
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return self.is_superuser
