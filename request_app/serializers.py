from rest_framework import serializers
from .models import Request
from user_app.serializers import UserSerializer

class RequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='user_id', read_only=True)
    
    class Meta:
        model = Request
        fields = ['id', 'uuid', 'user_id', 'user', 'description', 'type', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'user_id', 'status', 'created_at', 'updated_at']
