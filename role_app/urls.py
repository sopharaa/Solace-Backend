from django.urls import path
from . import views

urlpatterns = [
    path('auth/select-role', views.select_role, name='select_role'),
    path('admin/role-requests', views.list_role_requests, name='list_role_requests'),
    path('admin/role-requests/<int:pk>', views.review_role_request, name='review_role_request'),

    # Admin CRUD for roles
    path('admin/roles', views.list_or_create_role, name='list_create_roles'),
    path('admin/roles/<int:pk>', views.role_detail, name='role_detail'),
]
