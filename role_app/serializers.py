from rest_framework import serializers
from .models import Role
from user_app.models import User


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


