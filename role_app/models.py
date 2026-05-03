import uuid as _uuid
from django.db import models


class Role(models.Model):
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=20)
    permission = models.JSONField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


