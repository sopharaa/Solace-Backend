from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    confession_uuid = serializers.SerializerMethodField()
    comment_uuid = serializers.SerializerMethodField()
    request_uuid = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'uuid', 'message', 'type', 'status',
            'confession_uuid', 'comment_uuid', 'request_uuid',
            'created_at',
        ]

    def get_confession_uuid(self, obj):
        return str(obj.confession.uuid) if obj.confession else None

    def get_comment_uuid(self, obj):
        return str(obj.comment.uuid) if obj.comment else None

    def get_request_uuid(self, obj):
        return str(obj.request.uuid) if obj.request else None
