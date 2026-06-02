from rest_framework import serializers
from django.contrib.auth import authenticate
import requests
from .models import User


class RoleInlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    permission = serializers.JSONField()


class PromotedBySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['uuid', 'name', 'email']

class UserSerializer(serializers.ModelSerializer):
    role = RoleInlineSerializer(read_only=True)
    positions = serializers.SerializerMethodField()
    promoted_by = PromotedBySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'uuid', 'name', 'email', 'role', 'positions', 'status', 'avatar_url', 'promoted_by', 'created_at', 'updated_at']

    def get_positions(self, obj):
        from position_app.models import StaffPosition
        staff_positions = StaffPosition.objects.filter(
            user=obj, deleted_at__isnull=True
        ).select_related('position')
        return [sp.position.name for sp in staff_positions]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        if user.status == User.Status.BANNED:
            raise serializers.ValidationError('This account has been banned.')
        data['user'] = user
        return data


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    def validate_id_token(self, value):
        """Verify the Google ID token via Google's tokeninfo endpoint."""
        resp = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': value},
        )
        if resp.status_code != 200:
            raise serializers.ValidationError('Invalid or expired Google ID token.')

        data = resp.json()
        if not data.get('email'):
            raise serializers.ValidationError('Could not retrieve email from Google.')

        return data  # contains sub, email, name, picture, etc.

    def validate(self, data):
        userinfo = data.get('id_token')
        if userinfo:
            email = userinfo.get('email')
            user = User.objects.filter(email=email).first()
            if user and user.status == User.Status.BANNED:
                raise serializers.ValidationError('This account has been banned.')
        return data

    def create(self, validated_data):
        userinfo = validated_data['id_token']
        email = userinfo['email']
        google_id = userinfo['sub']


        user = User.objects.filter(email=email).first()
        if user:
            if user.deleted_at is not None:
                # Anonymize old record's unique fields so a new record can be created
                deleted_ts = int(user.deleted_at.timestamp())
                user.email = f"{user.email}_deleted_{deleted_ts}"
                if user.provider_id:
                    user.provider_id = f"{user.provider_id}_deleted_{deleted_ts}"
                user.save(update_fields=['email', 'provider_id', 'updated_at'])

                # Create a brand-new user record
                return User.objects.create_user(
                    email=email,
                    name=userinfo.get('name', ''),
                    provider_id=google_id,
                    avatar_url=userinfo.get('picture', ''),
                    status=User.Status.APPROVED,
                )

            # Existing non-deleted user — normal login
            if not user.provider_id:
                user.provider_id = google_id
                user.save(update_fields=['provider_id'])
            return user

        # Brand-new user
        user = User.objects.create_user(
            email=email,
            name=userinfo.get('name', ''),
            provider_id=google_id,
            avatar_url=userinfo.get('picture', ''),
            status=User.Status.APPROVED,
        )
        return user

