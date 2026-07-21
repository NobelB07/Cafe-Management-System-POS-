from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('signup/', views.signup, name='signup'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('customer/', views.customer_portal, name='customer_portal'),
    path('customer/order/', views.customer_order_create, name='customer_order_create'),
    path('admin-section/', views.admin_portal, name='admin_portal'),
    path('admin-section/users/create/', views.admin_user_create, name='admin_user_create'),
    path('admin-section/users/<int:user_id>/role/', views.user_role_update, name='user_role_update'),
    
    # Menu Management
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/create/', views.menu_create, name='menu_create'),
    path('menu/<int:pk>/edit/', views.menu_edit, name='menu_edit'),
    path('menu/<int:pk>/delete/', views.menu_delete, name='menu_delete'),
    
    # Order Management
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update-status/', views.order_update_status, name='order_update_status'),
    path('orders/<int:pk>/verify/', views.order_verify, name='order_verify'),
    path('orders/<int:pk>/remove-item/<int:item_pk>/', views.order_remove_item, name='order_remove_item'),
    path('orders/<int:pk>/apply-coupon/', views.order_apply_coupon, name='order_apply_coupon'),
    path('orders/<int:pk>/remove-coupon/', views.order_remove_coupon, name='order_remove_coupon'),
    path('orders/<int:pk>/payment/', views.order_select_payment, name='order_select_payment'),
    path('orders/<int:pk>/payment/esewa/', views.order_esewa_payment, name='order_esewa_payment'),
    path('orders/<int:pk>/payment/esewa/success/', views.order_esewa_success, name='order_esewa_success'),
    path('orders/<int:pk>/invoice/', views.order_invoice, name='order_invoice'),
]
