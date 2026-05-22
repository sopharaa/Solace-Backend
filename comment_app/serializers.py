from rest_framework import serializers
from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    """Read serializer — includes sender info for display."""
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    user_uuid = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'uuid', 'content', 'is_anonymous',
            'sender_name', 'sender_role', 'user_uuid', 'avatar_url',
            'created_at', 'updated_at',
        ]

    def get_sender_name(self, obj):
        if obj.is_anonymous:
            return 'Anonymous Staff'
        return obj.user.name

    def get_sender_role(self, obj):
        from position_app.models import StaffPosition
        positions = list(
            StaffPosition.objects.filter(user=obj.user, deleted_at__isnull=True)
            .select_related('position')
            .values_list('position__name', flat=True)
        )
        if positions:
            return ', '.join(positions)
        return obj.user.role.name if obj.user.role else ''

    def get_user_uuid(self, obj):
        return str(obj.user.uuid)

    def get_avatar_url(self, obj):
        if obj.is_anonymous:
            return None
        return obj.user.avatar_url


class CreateCommentSerializer(serializers.Serializer):
    """Input for creating a staff comment on a confession."""
    content = serializers.CharField()
    is_anonymous = serializers.BooleanField(default=False)
