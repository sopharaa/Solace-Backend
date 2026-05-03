import uuid as _uuid
from django.db import models


class State(models.Model):
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=30)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'states'

    def __str__(self):
        return self.name
