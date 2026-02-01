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
    path('user-completion-stats/', views.user_product_completion_stats, name='user-product-completion-stats'),
    path('user/products/', views.get_user_products_by_min_orders, name='get-user-products-by-min-orders'),
    path('admin/user/<int:user_id>/products/', views.get_user_products_for_admin, name='get-user-products-for-admin'),
    path('admin/user/<int:user_id>/completed-count/', views.get_user_completed_products_count, name='get-user-completed-products-count'),
    path('admin/user/<int:user_id>/level-journey-completed/', views.user_level_journey_completed, name='user-level-journey-completed'),
    path('level-journey-completed/', views.current_user_level_journey_completed, name='current-user-level-journey-completed'),
    path('<int:product_id>/position/', views.insert_product_at_position, name='insert-product-at-position'),
]

