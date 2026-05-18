import uuid as _uuid
from django.db import models
from user_app.models import User
from comment_app.models import Comment
from request_app.models import Request


class Notification(models.Model):
    class Status(models.TextChoices):
        UNREAD = 'UNREAD', 'Unread'
        READ = 'READ', 'Read'

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications',
        db_column='user_id'
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True,
        db_column='comment_id'
    )
    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True,
        db_column='request_id'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNREAD
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"Notification {self.uuid} - {self.status}"
