from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('admin/login', views.admin_login, name='admin_login'),
    path('auth/google', views.google_login, name='google_login'),
    path('auth/google/callback', views.google_auth_callback, name='google_auth_callback'),

    path('admin/logout', views.logout, name='logout'),
    path('auth/google/logout', views.logout, name='logout'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me', views.me, name='auth_me'),
    path('users', views.get_users, name='get_users'),
    path('users/<uuid:uuid>', views.user_detail, name='user_detail'),
    path('admin/verify-password', views.admin_verify_password, name='admin_verify_password'),
]
