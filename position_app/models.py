import uuid as _uuid
from django.db import models

class Position(models.Model):
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=30)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'positions'

    def __str__(self):
        return self.name


class StaffPosition(models.Model):
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='staff_positions'
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='staff_positions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'staff_positions'
        unique_together = ('user', 'position')

    def __str__(self):
        return f'{self.user.email} — {self.position.name}'

