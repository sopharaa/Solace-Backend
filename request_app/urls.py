from django.urls import path
from . import views

urlpatterns = [
    path('requests/', views.get_all_requests, name='get_all_requests'),
    path('requests/create/', views.create_request, name='create_request'),
    path('requests/<uuid:uuid>/respond/', views.respond_request, name='respond_request'),
]
