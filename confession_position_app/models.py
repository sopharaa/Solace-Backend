import uuid as _uuid
from django.db import models


class ConfessionPosition(models.Model):

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    confession = models.ForeignKey(
        'confession_app.Confession', on_delete=models.CASCADE, related_name='positions'
    )
    position = models.ForeignKey(
        'position_app.Position', on_delete=models.CASCADE, related_name='confessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'confession_positions'
        unique_together = ('confession', 'position')

    def __str__(self):
        return f'{self.confession.title} — {self.position.name}'
