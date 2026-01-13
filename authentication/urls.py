from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', views.RefreshTokenView.as_view(), name='token-refresh'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('check-auth/', views.check_auth_view, name='check-auth'),

    path('admin/users/', views.AdminUserListView.as_view(), name='admin-users-list'),
    path('admin/users/<int:id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:user_id>/change-role/', views.admin_change_user_role, name='admin-change-role'),
    path('admin/dashboard/stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    path('admin/users/<int:user_id>/activate/', views.admin_activate_user, name='admin-activate-user'),
    path('admin/users/<int:user_id>/deactivate/', views.admin_deactivate_user, name='admin-deactivate-user'),
    
    
    path('agent/dashboard/stats/', views.agent_dashboard_stats, name='agent-dashboard-stats'),
    path('agent/users/', views.agent_user_list, name='agent-user-list'),
]
