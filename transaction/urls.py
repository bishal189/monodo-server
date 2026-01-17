from django.urls import path
from . import views

app_name = 'transaction'

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list-create'),
    path('<int:id>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('my-transactions/', views.get_my_transactions, name='get-my-transactions'),
    path('my-balance/', views.get_my_balance, name='get-my-balance'),
    path('my-deposit/', views.my_deposit, name='my-deposit'),
    path('withdraw/', views.withdraw_amount, name='withdraw-amount'),
    path('<int:transaction_id>/approve/', views.approve_transaction, name='approve-transaction'),
    path('<int:transaction_id>/reject/', views.reject_transaction, name='reject-transaction'),
    path('add-balance/', views.add_balance, name='add-balance'),
]

