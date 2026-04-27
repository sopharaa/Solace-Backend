from django.db import models


class BlacklistedAccessToken(models.Model):
    jti = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blacklisted_access_tokens'

    def __str__(self):
        return self.jti
