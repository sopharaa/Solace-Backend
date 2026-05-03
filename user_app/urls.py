from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('admin/login', views.admin_login, name='admin_login'),
    path('auth/google', views.google_login, name='google_login'),

    path('admin/logout', views.logout, name='logout'),
    path('auth/google/logout', views.logout, name='logout'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me', views.me, name='auth_me'),
    path('users', views.get_users, name='get_users'),
]
