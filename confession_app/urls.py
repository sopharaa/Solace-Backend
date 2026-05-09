from django.urls import path
from . import views

urlpatterns = [
    path('confessions', views.confession_list_create, name='confession_list_create'),
    path('confessions/<uuid:uuid>', views.confession_detail, name='confession_detail'),
]
