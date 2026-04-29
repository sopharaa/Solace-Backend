from django.urls import path
from . import views

urlpatterns = [
    path('admin/login', views.admin_login, name='admin_login'),
    path('auth/google', views.google_login, name='google_login'),

    path('admin/logout', views.logout, name='logout'),
    path('auth/google/logout', views.logout, name='logout'),
    path('users', views.get_users, name='get_users'),
]
