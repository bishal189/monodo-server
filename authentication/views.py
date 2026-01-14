from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import User


def get_time_ago(dt):
    """Calculate time ago string from datetime"""
    if not dt:
        return None
    
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "1 day ago"
        return f"{diff.days} days ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        if hours == 1:
            return "1 hour ago"
        return f"{hours} hours ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        if minutes == 1:
            return "1 min ago"
        return f"{minutes} mins ago"
    else:
        return "Just now"


def get_user_initials(username):
    """Get initials from username (first letter of first two words)"""
    if not username:
        return ""
    parts = username.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1:
        return parts[0][:2].upper()
    return ""
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    AgentCreateSerializer
)
from .permissions import IsAdmin, IsAdminOrAgent
from activity.utils import create_login_activity


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'errors': serializer.errors,
                'message': 'Validation failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'message': 'Account created successfully',
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        create_login_activity(user, request)
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class RefreshTokenView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserProfileSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_auth_view(request):
    return Response({
        'authenticated': True,
        'user': UserProfileSerializer(request.user).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_user_role_view(request):
    return Response({
        'is_admin': request.user.is_admin,
        'is_agent': request.user.is_agent,
        'is_user': request.user.is_normal_user,
        'role': request.user.role,
        'user_id': request.user.id,
        'username': request.user.username,
        'email': request.user.email
    }, status=status.HTTP_200_OK)


class AdminUserListView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(username__icontains=search) |
                Q(phone_number__icontains=search)
            )
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role.upper())
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserProfileSerializer
        return UserUpdateSerializer
    
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': 'User deactivated successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def admin_dashboard_stats(request):
    if request.user.is_admin:
        user_queryset = User.objects.all()
        agent_queryset = User.objects.filter(role='AGENT')
    else:
        user_queryset = User.objects.filter(created_by=request.user)
        agent_queryset = User.objects.filter(role='AGENT', created_by=request.user)
    
    active_session = user_queryset.exclude(last_login__isnull=True).count()
    
    recent_users = user_queryset.exclude(
        last_login__isnull=True
    ).order_by('-last_login')[:5]
    
    top_users = []
    for user in recent_users:
        top_users.append({
            'id': user.id,
            'initials': get_user_initials(user.username),
            'name': user.username,
            'email': user.email,
            'time_ago': get_time_ago(user.last_login),
            'status': 'Active' if user.is_active else 'Inactive'
        })
    
    return Response({
        'total_users': user_queryset.count(),
        'active_session': active_session,
        'total_agent': agent_queryset.count(),
        'suspended_users': user_queryset.filter(is_active=False).count(),
        'top_recent_users': top_users
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdmin])
def admin_activate_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        return Response({
            'message': 'User activated successfully',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdmin])
def admin_deactivate_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return Response({
            'message': 'User deactivated successfully',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdmin])
def admin_change_user_role(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        new_role = request.data.get('role', '').upper()
        if new_role not in ['ADMIN', 'AGENT', 'USER']:
            return Response({'error': 'Invalid role. Must be ADMIN, AGENT, or USER'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = new_role
        if new_role == 'ADMIN':
            user.is_staff = True
        user.save()
        return Response({
            'message': f'User role changed to {new_role}',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def agent_dashboard_stats(request):
    return Response({
        'total_users': User.objects.filter(role='USER').count(),
        'active_users': User.objects.filter(role='USER', is_active=True).count(),
        'recent_registrations': User.objects.filter(
            role='USER',
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def agent_user_list(request):
    queryset = User.objects.filter(role='AGENT').order_by('-date_joined')
    search = request.query_params.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(phone_number__icontains=search)
        )
    serializer = UserProfileSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminOrAgent])
def agent_created_users_list(request):
    if request.user.is_admin:
        queryset = User.objects.filter(created_by__role='AGENT').order_by('-date_joined')
    else:
        queryset = User.objects.filter(created_by=request.user).order_by('-date_joined')
    
    search = request.query_params.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    is_active = request.query_params.get('is_active', None)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    role = request.query_params.get('role', None)
    if role:
        queryset = queryset.filter(role=role.upper())
    
    serializer = UserProfileSerializer(queryset, many=True)
    return Response({
        'users': serializer.data,
        'count': queryset.count()
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def agent_create_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                errors[field] = error_list[0] if error_list else 'Invalid value'
            else:
                errors[field] = str(error_list)
        
        return Response({
            'message': 'Validation failed',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    user.created_by = request.user
    user.save()
    
    return Response({
        'message': 'User created successfully',
        'user': UserProfileSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def agent_activate_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if not request.user.is_admin:
            if user.created_by != request.user:
                return Response({
                    'error': 'You can only activate users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        user.is_active = True
        user.save()
        return Response({
            'message': 'User activated successfully',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def agent_deactivate_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if not request.user.is_admin:
            if user.created_by != request.user:
                return Response({
                    'error': 'You can only deactivate users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        user.is_active = False
        user.save()
        return Response({
            'message': 'User deactivated successfully',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class AgentCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = AgentCreateSerializer
    permission_classes = [IsAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = {}
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    errors[field] = error_list[0] if error_list else 'Invalid value'
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        agent = serializer.save(created_by=request.user)
        return Response({
            'message': 'Agent created successfully',
            'user': UserProfileSerializer(agent).data
        }, status=status.HTTP_201_CREATED)
