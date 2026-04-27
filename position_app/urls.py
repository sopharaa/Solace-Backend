from django.urls import path
from . import views

urlpatterns = [
    path('admin/positions/', views.list_or_create_position, name='list_create_positions'),
    path('admin/positions/<int:pk>', views.position_detail, name='position_detail'),
    path('admin/positions/<int:pk>/toggle', views.toggle_position, name='toggle_position'),

    path('admin/staff/<int:pk>/positions', views.assign_positions, name='assign_positions'),
]
