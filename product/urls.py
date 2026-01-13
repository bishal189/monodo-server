from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product-list-create'),
    path('<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
]

