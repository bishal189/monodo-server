from django.urls import path
from . import views

app_name = 'activity'

urlpatterns = [
    path('login-activities/', views.LoginActivityListView.as_view(), name='login-activities'),
]

