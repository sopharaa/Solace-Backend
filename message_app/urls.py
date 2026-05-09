from django.urls import path
from . import views

urlpatterns = [
    path('confessions/<uuid:uuid>/messages', views.send_message, name='send_message'),
]
