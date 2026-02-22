from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from .models import Level
from .serializers import LevelSerializer, LevelCreateSerializer, LevelUpdateSerializer, AssignLevelSerializer
from authentication.permissions import IsAdminOrAgent
from authentication.models import User


class LevelListView(generics.ListCreateAPIView):
    """
    GET: List all levels
    POST: Create a new level
    """
    permission_classes = [IsAdminOrAgent]
    
    def get_queryset(self):
        queryset = Level.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        # Search by level name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(level_name__icontains=search) |
                Q(level__icontains=search)
            )
        
        return queryset.order_by('level')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LevelCreateSerializer
        return LevelSerializer
    
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
        
        level = serializer.save()
        return Response({
            'message': 'Level created successfully',
            'level': LevelSerializer(level).data
        }, status=status.HTTP_201_CREATED)


class LevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific level
    PUT/PATCH: Update a specific level
    DELETE: Delete a specific level
    """
    queryset = Level.objects.all()
    permission_classes = [IsAdminOrAgent]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LevelUpdateSerializer
        return LevelSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
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
        
        level = serializer.save()
        return Response({
            'message': 'Level updated successfully',
            'level': LevelSerializer(level).data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        level = self.get_object()
        level.delete()
        return Response({
            'message': 'Level deleted successfully'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminOrAgent])
def assign_level_to_user(request):
    """
    Assign a level to a particular user.
    POST: Assign or update user's level
    """
    serializer = AssignLevelSerializer(data=request.data)
    
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
    
    user_id = serializer.validated_data['user_id']
    level_id = serializer.validated_data['level_id']
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check permissions - agents can only assign levels to users they created
        if not request.user.is_admin:
            if user.created_by != request.user:
                return Response({
                    'error': 'You can only assign levels to users created by you'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Assign or remove level
        if level_id is not None:
            level = Level.objects.get(id=level_id)
            user.level = level
            message = f'Level "{level.level_name}" assigned to user successfully'
        else:
            user.level = None
            message = 'Level removed from user successfully'
        
        user.save()

        from product.views import reset_continuous_orders_for_user, reset_user_level_progress_impl
        reset_continuous_orders_for_user(user)
        if level_id is not None:
            reset_user_level_progress_impl(user, level)

        from authentication.serializers import UserProfileSerializer
        return Response({
            'message': message,
            'user': UserProfileSerializer(user).data,
            'level': LevelSerializer(user.level).data if user.level else None
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Level.DoesNotExist:
        return Response({
            'error': 'Level not found'
        }, status=status.HTTP_404_NOT_FOUND)
