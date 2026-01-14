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
    path('check-role/', views.check_user_role_view, name='check-role'),

    path('admin/users/', views.AdminUserListView.as_view(), name='admin-users-list'),
    path('admin/users/<int:id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:user_id>/change-role/', views.admin_change_user_role, name='admin-change-role'),
    path('admin/dashboard/stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    path('admin/users/<int:user_id>/activate/', views.admin_activate_user, name='admin-activate-user'),
    path('admin/users/<int:user_id>/deactivate/', views.admin_deactivate_user, name='admin-deactivate-user'),
    path('admin/agents/', views.admin_created_agents_list, name='admin-created-agents-list'),
    path('admin/agents/create/', views.AgentCreateView.as_view(), name='admin-create-agent'),
    path('admin/agents/users/', views.admin_all_agent_created_users, name='admin-all-agent-created-users'),
    
    path('agent/dashboard/stats/', views.agent_dashboard_stats, name='agent-dashboard-stats'),
    path('agent/users/', views.agent_user_list, name='agent-user-list'),
    path('agent/my-users/', views.agent_my_created_users, name='agent-my-created-users'),
    path('agent/created-users/', views.agent_created_users_list, name='agent-created-users-list'),
    path('agent/users/create/', views.agent_create_user, name='agent-create-user'),
    path('agent/users/<int:user_id>/activate/', views.agent_activate_user, name='agent-activate-user'),
    path('agent/users/<int:user_id>/deactivate/', views.agent_deactivate_user, name='agent-deactivate-user'),
]
