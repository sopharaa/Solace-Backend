from rest_framework import serializers
from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    """Read serializer — includes sender info for display."""
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'uuid', 'content', 'is_anonymous',
            'sender_name', 'sender_role',
            'created_at', 'updated_at',
        ]

    def get_sender_name(self, obj):
        if obj.is_anonymous:
            return 'Anonymous Staff'
        return obj.user.name

    def get_sender_role(self, obj):
        return obj.user.role.name if obj.user.role else ''


class CreateCommentSerializer(serializers.Serializer):
    """Input for creating a staff comment on a confession."""
    content = serializers.CharField()
    is_anonymous = serializers.BooleanField(default=False)
