import uuid as _uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser):
    class Status(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        PENDING = 'PENDING', 'Pending'
        REJECTED = 'REJECTED', 'Rejected'
        BANNED = 'BANNED', 'Banned'

    uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    role = models.ForeignKey('role_app.Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    provider_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    promoted_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='promoted_users')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
