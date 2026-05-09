import uuid as _uuid
from django.db import models


class ConfessionState(models.Model):

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    confession = models.ForeignKey(
        'confession_app.Confession', on_delete=models.CASCADE, related_name='states'
    )
    state = models.ForeignKey(
        'state_app.State', on_delete=models.CASCADE, related_name='confessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'confession_states'
        unique_together = ('confession', 'state')

    def __str__(self):
        return f'{self.confession.title} — {self.state.name}'
