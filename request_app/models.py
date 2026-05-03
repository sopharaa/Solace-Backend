import uuid as _uuid
from django.db import models
from user_app.models import User


class Request(models.Model):
    class Status(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        PENDING = 'PENDING', 'Pending'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    description = models.TextField()
    type = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'requests'

    def __str__(self):
        return f"Request {self.uuid} - {self.status}"
