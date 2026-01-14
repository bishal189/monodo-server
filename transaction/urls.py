from django.urls import path
from . import views

app_name = 'transaction'

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list-create'),
    path('<int:id>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
]

