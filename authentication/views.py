from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from django.db.models import Q, Count
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


def format_user_table_data(users_queryset):
    """Helper function to format users in table-friendly format"""
    table_data = []
    for user in users_queryset:
        level_name = None
        level_id = None
        if user.level:
            level_name = user.level.level_name
            level_id = user.level.id
        
        account_type = 'Training' if user.is_training_account else 'Original'
        
        original_account_info = None
        if user.is_training_account and user.original_account:
            original_account_info = {
                'id': user.original_account.id,
                'username': user.original_account.username,
                'email': user.original_account.email
            }
        
        table_data.append({
            'id': user.id,
            'account_type': account_type,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'invitation_code': user.invitation_code,
            'original_account': original_account_info,
            'balance': float(user.balance),
            'role': user.role,
            'level': {
                'id': level_id,
                'name': level_name
            } if level_name else None,
            'created_by': {
                'id': user.created_by.id if user.created_by else None,
                'username': user.created_by.username if user.created_by else None,
                'email': user.created_by.email if user.created_by else None
            },
            'status': 'Active' if user.is_active else 'Inactive',
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_training_account': user.is_training_account
        })
    return table_data


from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    AdminAgentEditUserSerializer,
    AgentCreateSerializer,
    TrainingAccountCreateSerializer,
    AgentProfileUpdateSerializer
)
from .permissions import IsAdmin, IsAdminOrAgent, IsAgent
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
            errors = {}
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    if len(error_list) == 1:
                        errors[field] = error_list[0]
                    else:
                        errors[field] = error_list
                elif isinstance(error_list, dict):
                    errors[field] = error_list
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'success': True,
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
        return Response({
            **tokens,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'role': user.role,
                'is_admin': user.is_admin,
                'is_agent': user.is_agent,
                'is_normal_user': user.is_normal_user
            }
        }, status=status.HTTP_200_OK)
    
    errors = {}
    error_message = None
    
    if isinstance(serializer.errors, dict):
        if 'non_field_errors' in serializer.errors:
            error_list = serializer.errors['non_field_errors']
            if isinstance(error_list, list) and error_list:
                error_message = error_list[0]
            else:
                error_message = str(error_list)
        
        if not error_message:
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list) and error_list:
                    error_message = error_list[0]
                    break
                else:
                    error_message = str(error_list)
                    break
        
        errors = serializer.errors
    
    if not error_message:
        error_message = 'Invalid email or password.'
    
    return Response({
        'error': error_message,
        'errors': errors,
        'message': error_message
    }, status=status.HTTP_400_BAD_REQUEST)


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
def get_invitation_code(request):
    """
    Get the invitation code and level for the currently logged-in user.
    """
    user = request.user
    
    # Get level information if available
    level_data = None
    if user.level:
        from level.serializers import LevelSerializer
        level_data = LevelSerializer(user.level).data
    
    return Response({
        'invitation_code': user.invitation_code,
        'username': user.username,
        'email': user.email,
        'level': level_data
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
def agent_my_created_users(request):
    """
    Get all users created by the currently logged-in user (agent or admin).
    Includes both original accounts and training accounts created by the agent.
    Returns structured data showing relationship between original and training accounts.
    Accessible by both admins and agents.
    """
    queryset = User.objects.filter(created_by=request.user).select_related('level', 'original_account', 'created_by').prefetch_related('training_accounts').order_by('-date_joined')
    
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
    
    is_training_account = request.query_params.get('is_training_account', None)
    if is_training_account is not None:
        queryset = queryset.filter(is_training_account=is_training_account.lower() == 'true')
    
    all_users = queryset
    original_accounts = all_users.filter(is_training_account=False)
    training_accounts = all_users.filter(is_training_account=True)
    
    original_accounts_serializer = UserProfileSerializer(original_accounts, many=True)
    training_accounts_serializer = UserProfileSerializer(training_accounts, many=True)
    
    structured_data = []
    original_accounts_dict = {}
    
    for original_account_data in original_accounts_serializer.data:
        original_account_id = original_account_data['id']
        original_accounts_dict[original_account_id] = {
            **original_account_data,
            'training_accounts': []
        }
    
    for training_account_data in training_accounts_serializer.data:
        original_account_id = training_account_data.get('original_account_id')
        if original_account_id and original_account_id in original_accounts_dict:
            original_accounts_dict[original_account_id]['training_accounts'].append(training_account_data)
        else:
            structured_data.append({
                **training_account_data,
                'training_accounts': []
            })
    
    for account_data in original_accounts_dict.values():
        structured_data.append(account_data)
    
    structured_data.sort(key=lambda x: x['date_joined'], reverse=True)
    
    return Response({
        'users': structured_data,
        'count': all_users.count()
    }, status=status.HTTP_200_OK)


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
                if len(error_list) == 1:
                    errors[field] = error_list[0]
                else:
                    errors[field] = error_list
            elif isinstance(error_list, dict):
                errors[field] = error_list
            else:
                errors[field] = str(error_list)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    user.created_by = request.user
    user.save()
    
    return Response({
        'success': True,
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


@api_view(['GET', 'PATCH', 'PUT'])
@permission_classes([IsAdminOrAgent])
def edit_user(request, user_id):
    """
    Get or update a user. Allowed for admin and agent.
    Admin can edit any USER-role user. Agent can only edit users they created.
    """
    try:
        target_user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin and target_user.created_by != request.user:
        return Response({
            'error': 'You can only edit users created by you'
        }, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response({
            'user': UserProfileSerializer(target_user).data
        }, status=status.HTTP_200_OK)

    # PATCH or PUT
    partial = request.method == 'PATCH'
    serializer = AdminAgentEditUserSerializer(target_user, data=request.data, partial=partial)
    if not serializer.is_valid():
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                errors[field] = error_list[0] if len(error_list) == 1 else error_list
            else:
                errors[field] = str(error_list)
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)

    updated_user = serializer.save()
    return Response({
        'success': True,
        'message': 'User updated successfully',
        'user': UserProfileSerializer(updated_user).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_created_agents_list(request):
    """
    Get all agents created by admins with total users count.
    Only accessible by admins.
    Returns: ID, Name, Email, Phone, Invitation Code, Total Users, Status, Created By, Created At
    """
    queryset = User.objects.filter(
        role='AGENT', 
        created_by__role='ADMIN'
    ).annotate(
        total_users=Count('created_users')
    ).select_related('created_by').order_by('-date_joined')
    
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
    
    agents_data = []
    for agent in queryset:
        agents_data.append({
            'id': agent.id,
            'name': agent.username,
            'email': agent.email,
            'phone': agent.phone_number,
            'invitation_code': agent.invitation_code,
            'total_users': agent.total_users,
            'status': 'Active' if agent.is_active else 'Inactive',
            'created_by': agent.created_by.username if agent.created_by else None,
            'created_by_email': agent.created_by.email if agent.created_by else None,
            'created_at': agent.date_joined.isoformat() if agent.date_joined else None
        })
    
    return Response({
        'agents': agents_data,
        'count': len(agents_data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_all_agent_created_users(request):
    """
    Get all users created by all agents.
    Includes both original accounts and training accounts created by agents.
    Returns structured data showing relationship between original and training accounts.
    Only accessible by admins.
    """
    queryset = User.objects.filter(created_by__role='AGENT').select_related('created_by', 'level', 'original_account').prefetch_related('training_accounts').order_by('-date_joined')
    
    search = request.query_params.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(invitation_code__icontains=search)
        )
    
    is_active = request.query_params.get('is_active', None)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    role = request.query_params.get('role', None)
    if role:
        queryset = queryset.filter(role=role.upper())
    
    is_training_account = request.query_params.get('is_training_account', None)
    if is_training_account is not None:
        queryset = queryset.filter(is_training_account=is_training_account.lower() == 'true')
    
    # Filter by specific agent if agent_id is provided
    agent_id = request.query_params.get('agent_id', None)
    if agent_id:
        queryset = queryset.filter(created_by_id=agent_id)
    
    all_users = queryset
    original_accounts = all_users.filter(is_training_account=False)
    training_accounts = all_users.filter(is_training_account=True)
    
    original_accounts_serializer = UserProfileSerializer(original_accounts, many=True)
    training_accounts_serializer = UserProfileSerializer(training_accounts, many=True)
    
    structured_data = []
    original_accounts_dict = {}
    
    for original_account_data in original_accounts_serializer.data:
        original_account_id = original_account_data['id']
        original_accounts_dict[original_account_id] = {
            **original_account_data,
            'training_accounts': []
        }
    
    for training_account_data in training_accounts_serializer.data:
        original_account_id = training_account_data.get('original_account_id')
        if original_account_id and original_account_id in original_accounts_dict:
            original_accounts_dict[original_account_id]['training_accounts'].append(training_account_data)
        else:
            structured_data.append({
                **training_account_data,
                'training_accounts': []
            })
    
    for account_data in original_accounts_dict.values():
        structured_data.append(account_data)
    
    structured_data.sort(key=lambda x: x['date_joined'], reverse=True)
    
    return Response({
        'users': structured_data,
        'count': all_users.count()
    }, status=status.HTTP_200_OK)


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
                    if len(error_list) == 1:
                        errors[field] = error_list[0]
                    else:
                        errors[field] = error_list
                elif isinstance(error_list, dict):
                    errors[field] = error_list
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        agent = serializer.save(created_by=request.user)
        return Response({
            'success': True,
            'message': 'Agent created successfully',
            'user': UserProfileSerializer(agent).data
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def create_training_account(request):
    serializer = TrainingAccountCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                if len(error_list) == 1:
                    errors[field] = error_list[0]
                else:
                    errors[field] = error_list
            elif isinstance(error_list, dict):
                errors[field] = error_list
            else:
                errors[field] = str(error_list)
        
        error_messages = []
        for field, message in errors.items():
            if isinstance(message, list):
                error_messages.extend([f"{field}: {msg}" for msg in message])
            else:
                error_messages.append(f"{field}: {message}")
        
        return Response({
            'success': False,
            'message': 'Validation failed. Please check the errors below.',
            'errors': errors,
            'error_summary': error_messages
        }, status=status.HTTP_400_BAD_REQUEST)
    
    training_account = serializer.save()
    
    return Response({
        'success': True,
        'message': 'Training account created successfully',
        'training_account': UserProfileSerializer(training_account).data,
        'original_account': UserProfileSerializer(training_account.original_account).data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_training_accounts(request, original_account_id):
    try:
        original_account = User.objects.get(id=original_account_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Original account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not request.user.is_admin and not request.user.is_agent:
        if original_account.id != request.user.id:
            return Response({
                'error': 'You do not have permission to view this information'
            }, status=status.HTTP_403_FORBIDDEN)
    
    training_accounts = original_account.training_accounts.filter(is_active=True).order_by('-date_joined')
    
    serializer = UserProfileSerializer(training_accounts, many=True)
    
    return Response({
        'original_account': UserProfileSerializer(original_account).data,
        'training_accounts': serializer.data,
        'count': training_accounts.count()
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_training_accounts(request):
    user = request.user
    
    if user.is_training_account and user.original_account:
        original_account = user.original_account
    else:
        original_account = user
    
    training_accounts = original_account.training_accounts.filter(is_active=True).order_by('-date_joined')
    
    serializer = UserProfileSerializer(training_accounts, many=True)
    
    return Response({
        'original_account': UserProfileSerializer(original_account).data,
        'training_accounts': serializer.data,
        'count': training_accounts.count()
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdmin])
def update_agent_profile(request, agent_id):
    if not request.user or not request.user.is_authenticated:
        return Response({
            'error': 'Authentication required'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not request.user.is_admin:
        return Response({
            'error': 'Only admins can update agent profiles'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        agent = User.objects.get(id=agent_id, role='AGENT')
        
        partial = request.method == 'PATCH'
        serializer = AgentProfileUpdateSerializer(agent, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            print(serializer.errors,'errors')
            errors = {}
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    if len(error_list) == 1:
                        errors[field] = error_list[0]
                    else:
                        errors[field] = error_list
                elif isinstance(error_list, dict):
                    errors[field] = error_list
                else:
                    errors[field] = str(error_list)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_agent = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Agent profile updated successfully',
            'agent': UserProfileSerializer(updated_agent).data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Update failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
