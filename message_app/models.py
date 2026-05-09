import uuid as _uuid
from django.db import models


class Message(models.Model):
    
    class MessageType(models.TextChoices):
        STUDENT = 'Student', 'Student'
        AI = 'AI', 'AI'

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    confession = models.ForeignKey(
        'confession_app.Confession', on_delete=models.CASCADE, related_name='messages'
    )
    content = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.STUDENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messages'

    def __str__(self):
        return f'{self.type} message on {self.confession.title}'
