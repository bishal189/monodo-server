from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product-list-create'),
    path('<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('assign-to-level/', views.assign_products_to_level, name='assign-products-to-level'),
    path('level/<int:level_id>/', views.get_products_by_level, name='get-products-by-level'),
    path('dashboard/', views.product_dashboard, name='product-dashboard'),
    path('review/', views.submit_product_review, name='submit-product-review'),
    path('reviews/', views.get_products_by_review_status, name='get-products-by-review-status'),
    path('reset/user/<int:user_id>/level/<int:level_id>/', views.reset_user_level_progress, name='reset-user-level-progress'),
]

