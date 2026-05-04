from django.urls import path
from . import views

urlpatterns = [
    path('positions/', views.list_active_positions, name='list_active_positions'),

    path('admin/positions/', views.list_or_create_position, name='list_create_positions'),
    path('admin/positions/<uuid:uuid>', views.position_detail, name='position_detail'),
    path('admin/positions/<uuid:uuid>/toggle', views.toggle_position, name='toggle_position'),

    path('admin/staff/<uuid:uuid>/positions', views.assign_positions, name='assign_positions'),
]
