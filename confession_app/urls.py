from django.urls import path
from . import views

urlpatterns = [
    path('confessions', views.confession_list_create, name='confession_list_create'),
    path('confessions/<uuid:uuid>', views.confession_detail, name='confession_detail'),
    # Staff endpoints
    path('staff/confessions', views.staff_confession_list, name='staff_confession_list'),
    path('staff/confessions/<uuid:uuid>', views.staff_confession_detail, name='staff_confession_detail'),
]
