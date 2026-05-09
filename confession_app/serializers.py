from rest_framework import serializers
from .models import Confession
from message_app.models import Message
from confession_state_app.models import ConfessionState
from confession_position_app.models import ConfessionPosition


class ConfessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing confessions (sidebar)."""
    states = serializers.SerializerMethodField()
    positions = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title', 'is_anonymous', 'is_archived',
            'states', 'positions', 'created_at', 'updated_at', 'last_message_at',
        ]

    def get_states(self, obj):
        return list(
            ConfessionState.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('state__name', flat=True)
        )

    def get_positions(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_last_message_at(self, obj):
        last = Message.objects.filter(
            confession=obj, deleted_at__isnull=True
        ).order_by('-created_at').first()
        return last.created_at if last else obj.created_at


class ConfessionDetailSerializer(serializers.ModelSerializer):
    """Full confession with messages."""
    states = serializers.SerializerMethodField()
    positions = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title', 'is_anonymous', 'is_archived',
            'states', 'positions', 'messages',
            'created_at', 'updated_at',
        ]

    def get_states(self, obj):
        return list(
            ConfessionState.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('state__name', flat=True)
        )

    def get_positions(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_messages(self, obj):
        from message_app.serializers import MessageSerializer
        msgs = Message.objects.filter(
            confession=obj, deleted_at__isnull=True
        ).order_by('created_at')
        return MessageSerializer(msgs, many=True).data


class CreateConfessionSerializer(serializers.Serializer):
    """Input for creating a new confession with first message."""
    message = serializers.CharField()
    is_anonymous = serializers.BooleanField(default=False)
    states = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    positions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
