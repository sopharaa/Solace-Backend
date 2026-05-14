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


class StudentCommentListSerializer(serializers.ModelSerializer):
    """Serializer for students to see their confessions with comment summaries."""
    comment_count = serializers.SerializerMethodField()
    last_comment_author = serializers.SerializerMethodField()
    last_comment_text = serializers.SerializerMethodField()
    last_comment_at = serializers.SerializerMethodField()
    positions = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'uuid', 'title', 'is_anonymous', 'is_archived',
            'comment_count', 'last_comment_author', 'last_comment_text',
            'last_comment_at', 'positions',
            'created_at', 'updated_at',
        ]

    def get_positions(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_comment_count(self, obj):
        return obj.comments.filter(deleted_at__isnull=True).count()

    def get_last_comment_author(self, obj):
        last = obj.comments.filter(deleted_at__isnull=True).order_by('-created_at').first()
        if not last:
            return ''
        if last.is_anonymous:
            return 'Anonymous Staff'
        return last.user.name

    def get_last_comment_text(self, obj):
        last = obj.comments.filter(deleted_at__isnull=True).order_by('-created_at').first()
        return last.content if last else ''

    def get_last_comment_at(self, obj):
        last = obj.comments.filter(deleted_at__isnull=True).order_by('-created_at').first()
        return last.created_at if last else None


class StudentCommentDetailSerializer(serializers.ModelSerializer):
    """Full confession with comments for student view-comment detail."""
    comments = serializers.SerializerMethodField()
    positions = serializers.SerializerMethodField()
    states = serializers.SerializerMethodField()
    expressions = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'uuid', 'title', 'is_anonymous', 'is_archived',
            'comments', 'positions', 'states', 'expressions',
            'created_at', 'updated_at',
        ]

    def get_comments(self, obj):
        from comment_app.serializers import CommentSerializer
        comments = obj.comments.filter(deleted_at__isnull=True).order_by('created_at')
        return CommentSerializer(comments, many=True, context={'request': self.context.get('request')}).data

    def get_positions(self, obj):
        return list(
            ConfessionPosition.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('position__name', flat=True)
        )

    def get_states(self, obj):
        return list(
            ConfessionState.objects.filter(confession=obj, deleted_at__isnull=True)
            .values_list('state__name', flat=True)
        )

    def get_expressions(self, obj):
        """Return the student's own messages (expressions)."""
        msgs = Message.objects.filter(
            confession=obj, deleted_at__isnull=True,
            type='Student'
        ).order_by('created_at')
        return [
            {
                'id': str(m.uuid),
                'content': m.content,
                'created_at': m.created_at.isoformat() if m.created_at else '',
            }
            for m in msgs
        ]


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
    student_avatar = serializers.SerializerMethodField()
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
            'student_avatar', 'is_student_anonymous',
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

    def get_student_avatar(self, obj):
        if obj.is_anonymous:
            return None
        return obj.user.avatar_url

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
    student_avatar = serializers.SerializerMethodField()
    is_student_anonymous = serializers.BooleanField(source='is_anonymous')
    emotions = serializers.SerializerMethodField()
    encouragements = serializers.SerializerMethodField()
    expressions = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title', 'student_name', 'student_email',
            'student_avatar', 'is_student_anonymous',
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

    def get_student_avatar(self, obj):
        if obj.is_anonymous:
            return None
        return obj.user.avatar_url

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


class AdminConfessionListSerializer(serializers.ModelSerializer):
    """Serializer for admin viewing ALL confessions with full identity info."""
    student_name = serializers.SerializerMethodField()
    real_student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    student_avatar = serializers.SerializerMethodField()
    is_anonymous = serializers.BooleanField()
    is_archived = serializers.BooleanField()
    emotions = serializers.SerializerMethodField()
    encouragements = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    expression_count = serializers.SerializerMethodField()
    last_student_expression = serializers.SerializerMethodField()

    class Meta:
        model = Confession
        fields = [
            'id', 'uuid', 'title',
            'student_name', 'real_student_name', 'student_email', 'student_avatar',
            'is_anonymous', 'is_archived',
            'emotions', 'encouragements',
            'comment_count', 'expression_count', 'last_student_expression',
            'created_at', 'updated_at',
        ]

    def get_student_name(self, obj):
        """Display name (respects anonymity)."""
        if obj.is_anonymous:
            return 'Anonymous Student'
        return obj.user.name

    def get_real_student_name(self, obj):
        """Always returns real name — admin only."""
        return obj.user.name

    def get_student_email(self, obj):
        """Always returns real email — admin only."""
        return obj.user.email

    def get_student_avatar(self, obj):
        """Always returns avatar — admin only."""
        return obj.user.avatar_url

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
