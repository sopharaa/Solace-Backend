from rest_framework import serializers
from .models import Role
from user_app.models import User


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'uuid', 'name', 'permission', 'created_at', 'updated_at', 'user_count']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']

    def validate_name(self, value):
        qs = Role.objects.filter(name__iexact=value, deleted_at__isnull=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A role with this name already exists.')
        return value


class SelectRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['STUDENT', 'STAFF'])

    def validate(self, data):
        user = self.context['request'].user
        if user.role is not None:
            raise serializers.ValidationError('Role has already been assigned.')
        return data

    def save(self):
        user = self.context['request'].user
        role_name = self.validated_data['role']

        role = Role.objects.get(name=role_name)
        user.role = role

        if role_name == 'STUDENT':
            user.status = User.Status.APPROVED
        else:  # STAFF
            user.status = User.Status.PENDING

        user.save(update_fields=['role', 'status'])
        return user


class ReviewRoleRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])

    def save(self):
        user = self.context['role_user']
        new_status = self.validated_data['status']

        user.status = new_status
        user.save(update_fields=['status'])
        return user
