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


class StaffConfessionListSerializer(serializers.ModelSerializer):
    """Serializer for staff viewing all confessions."""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    is_student_anonymous = serializers.BooleanField(source='is_anonymous')
    emotions = serializers.SerializerMethodField()
    encouragements = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    expression_count = serializers.SerializerMethodField()
    last_student_expression = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title', 'student_name', 'student_email',
            'is_student_anonymous',
            'emotions', 'encouragements',
            'comment_count', 'expression_count', 'last_student_expression',
            'created_at', 'updated_at',
        ]

    def get_student_name(self, obj):
        if obj.is_anonymous:
            return 'Anonymous Student'
        return obj.user.name

    def get_student_email(self, obj):
        if obj.is_anonymous:
            return None
        return obj.user.email

    def get_emotions(self, obj):
        return list(
            ConfessionState.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('state__name', flat=True)
        )

    def get_encouragements(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_comment_count(self, obj):
        return obj.comments.filter(deleted_at__isnull=True).count()

    def get_expression_count(self, obj):
        return Message.objects.filter(
            confession=obj, deleted_at__isnull=True,
            type='Student'
        ).count()

    def get_last_student_expression(self, obj):
        last = Message.objects.filter(
            confession=obj, deleted_at__isnull=True,
            type='Student'
        ).order_by('-created_at').first()
        return last.content if last else None


class StaffConfessionDetailSerializer(serializers.ModelSerializer):
    """Full confession detail for staff — includes student messages and comments."""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    is_student_anonymous = serializers.BooleanField(source='is_anonymous')
    emotions = serializers.SerializerMethodField()
    encouragements = serializers.SerializerMethodField()
    expressions = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title', 'student_name', 'student_email',
            'is_student_anonymous',
            'emotions', 'encouragements', 'expressions', 'comments',
            'created_at', 'updated_at',
        ]

    def get_student_name(self, obj):
        if obj.is_anonymous:
            return 'Anonymous Student'
        return obj.user.name

    def get_student_email(self, obj):
        if obj.is_anonymous:
            return None
        return obj.user.email

    def get_emotions(self, obj):
        return list(
            ConfessionState.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('state__name', flat=True)
        )

    def get_encouragements(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_expressions(self, obj):
        """Return student messages only (staff should not see AI responses)."""
        msgs = Message.objects.filter(
            confession=obj, deleted_at__isnull=True,
            type='Student'
        ).order_by('created_at')
        return [
            {
                'id': str(m.uuid),
                'content': m.content,
                'created_at': m.created_at,
            }
            for m in msgs
        ]

    def get_comments(self, obj):
        from comment_app.serializers import CommentSerializer
        comments = obj.comments.filter(deleted_at__isnull=True).order_by('created_at')
        return CommentSerializer(comments, many=True).data

