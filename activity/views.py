from django.db.models import Q

from rest_framework import generics, permissions
from .models import LoginActivity
from .serializers import LoginActivitySerializer


class LoginActivityListView(generics.ListAPIView):
    serializer_class = LoginActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = LoginActivity.objects.all().select_related('user')
        
        if self.request.user.is_admin:
            pass  # admin sees all
        elif self.request.user.is_agent:
            # agent sees own activity + activities of users they created
            queryset = queryset.filter(
                Q(user=self.request.user) | Q(user__created_by=self.request.user)
            )
        else:
            queryset = queryset.filter(user=self.request.user)
        
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            if self.request.user.is_admin:
                queryset = queryset.filter(user_id=user_id)
            elif self.request.user.is_agent:
                queryset = queryset.filter(user_id=user_id, user__created_by=self.request.user)
        
        device_type = self.request.query_params.get('device_type', None)
        if device_type:
            queryset = queryset.filter(device_type=device_type.upper())
        
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(login_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(login_time__lte=end_date)
        
        return queryset.order_by('-login_time')
