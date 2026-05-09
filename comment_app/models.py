import uuid as _uuid
from django.db import models
from user_app.models import User


class Comment(models.Model):

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    confession = models.ForeignKey(
        'confession_app.Confession', on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'comments'

    def __str__(self):
        return f'Comment by {self.user} on {self.confession.title}'
