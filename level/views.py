from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from .models import Level
from .serializers import LevelSerializer, LevelCreateSerializer, LevelUpdateSerializer
from authentication.permissions import IsAdmin


class LevelListView(generics.ListCreateAPIView):
    """
    GET: List all levels
    POST: Create a new level
    """
    permission_classes = [IsAdmin]
    
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
    permission_classes = [IsAdmin]
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
