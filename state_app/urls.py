from django.urls import path
from . import views

urlpatterns = [
    path('states/', views.list_active_states, name='list_active_states'),
    path('admin/states/', views.list_or_create_state, name='list_create_states'),
    path('admin/states/<int:pk>/', views.state_detail, name='state_detail'),
    path('admin/states/<int:pk>', views.state_detail, name='state_detail_no_slash'),
]