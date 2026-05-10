from django.urls import path
from . import views

urlpatterns = [
    path('confessions/<uuid:uuid>/comments', views.comment_list_create, name='comment_list_create'),
    path('comments/<uuid:uuid>', views.comment_delete, name='comment_delete'),
]
