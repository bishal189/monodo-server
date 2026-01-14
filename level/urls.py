from django.urls import path
from . import views

app_name = 'level'

urlpatterns = [
    path('', views.LevelListView.as_view(), name='level-list-create'),
    path('<int:id>/', views.LevelDetailView.as_view(), name='level-detail'),
    path('assign/', views.assign_level_to_user, name='assign-level-to-user'),
]

