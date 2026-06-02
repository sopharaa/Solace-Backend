from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import BlacklistedAccessToken


class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)

        jti = validated_token.get('jti')
        if BlacklistedAccessToken.objects.filter(jti=jti).exists():
            raise AuthenticationFailed('Token has been blacklisted.')

        return validated_token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed('User is inactive.')
        if user.status == 'BANNED':
            raise AuthenticationFailed('User has been banned.')
        if user.deleted_at is not None:
            raise AuthenticationFailed('User account has been deleted.')
        return user

