from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'uuid', 'content', 'type', 'created_at']


class CreateMessageSerializer(serializers.Serializer):
    """Input for sending a new message in an existing confession."""
    content = serializers.CharField()
