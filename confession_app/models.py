import uuid as _uuid
from django.db import models
from user_app.models import User


class Confession(models.Model):

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='confessions')
    title = models.CharField(max_length=255)
    is_anonymous = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'confessions'

    def __str__(self):
        return self.title
