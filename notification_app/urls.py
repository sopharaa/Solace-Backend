from django.urls import path
from . import views

urlpatterns = [
    path('api/v1/notifications', views.notification_list, name='notification-list'),
    path('api/v1/notifications/read-all', views.mark_all_read, name='notification-mark-all-read'),
    path('api/v1/notifications/unread-count', views.unread_count, name='notification-unread-count'),
    path('api/v1/notifications/<uuid:uuid>/read', views.mark_read, name='notification-mark-read'),
    path('api/v1/notifications/<uuid:uuid>', views.delete_notification, name='notification-delete'),
]
