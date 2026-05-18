from django.urls import path
from . import views

urlpatterns = [
    path('confessions', views.confession_list_create, name='confession_list_create'),
    path('confessions/<uuid:uuid>', views.confession_detail, name='confession_detail'),
    # Student comment endpoints
    path('confessions/comments', views.student_comment_list, name='student_comment_list'),
    path('confessions/<uuid:uuid>/comment-thread', views.student_comment_detail, name='student_comment_detail'),
    # Staff endpoints
    path('staff/confessions', views.staff_confession_list, name='staff_confession_list'),
    path('staff/confessions/<uuid:uuid>', views.staff_confession_detail, name='staff_confession_detail'),
    # Admin endpoints
    path('admin/confessions', views.admin_confession_list, name='admin_confession_list'),
    path('admin/confessions/<uuid:uuid>', views.admin_confession_detail, name='admin_confession_detail'),
    path('admin/dashboard-stats', views.admin_dashboard_stats, name='admin_dashboard_stats'),
]
