from django.utils import timezone
from rest_framework import serializers
from .models import Position, StaffPosition
from role_app.models import Role


class RoleInlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    uuid = serializers.UUIDField()
    name = serializers.CharField()


class PositionSerializer(serializers.ModelSerializer):
    assigned_count = serializers.IntegerField(read_only=True)
    role = RoleInlineSerializer(read_only=True)
    role_uuid = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Position
        fields = [
            'id', 'uuid', 'name', 'description', 'role', 'role_uuid',
            'is_active', 'created_at', 'updated_at', 'assigned_count',
        ]
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']

    def validate_name(self, value):
        # Exclude the current instance when updating
        qs = Position.objects.filter(name__iexact=value, is_active=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A position with this name already exists.')
        return value

    def validate_role_uuid(self, value):
        if value is None:
            return None
        try:
            return Role.objects.get(uuid=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError('Role not found.')

    def create(self, validated_data):
        role = validated_data.pop('role_uuid', None)
        instance = Position.objects.create(**validated_data)
        if role is not None:
            instance.role = role
            instance.save(update_fields=['role'])
        return instance

    def update(self, instance, validated_data):
        role = validated_data.pop('role_uuid', ...)  # sentinel to detect absence
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if role is not ...:  # only update role if explicitly provided
            instance.role = role
        instance.save()
        return instance



class AssignPositionsSerializer(serializers.Serializer):
    position_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True
    )

    def validate_position_ids(self, value):
        positions = Position.objects.select_related('role').filter(uuid__in=value, is_active=True)
        if len(positions) != len(value):
            found_ids = set(positions.values_list('uuid', flat=True))
            invalid_ids = [pid for pid in value if pid not in found_ids]
            raise serializers.ValidationError(f'Invalid or inactive position IDs: {invalid_ids}')

        # Enforce role match: position's role must match the user's role (if the position has a role)
        staff_user = self.context.get('staff_user')
        if staff_user and staff_user.role:
            user_role_id = staff_user.role.id
            mismatched = [
                p.name for p in positions
                if p.role is not None and p.role.id != user_role_id
            ]
            if mismatched:
                raise serializers.ValidationError(
                    f'The following positions do not belong to the user\'s role: {mismatched}'
                )
        return value

    def save(self):
        staff_user = self.context['staff_user']
        new_uuids = set(self.validated_data['position_ids'])
        new_ids = set(Position.objects.filter(uuid__in=new_uuids).values_list('id', flat=True))

        # Soft-delete removed positions
        StaffPosition.objects.filter(
            user=staff_user, deleted_at__isnull=True
        ).exclude(position_id__in=new_ids).update(deleted_at=timezone.now())

        # Restore or create new assignments
        for pid in new_ids:
            sp = StaffPosition.objects.filter(user=staff_user, position_id=pid).first()
            if sp:
                if sp.deleted_at is not None:
                    sp.deleted_at = None
                    sp.save(update_fields=['deleted_at', 'updated_at'])
            else:
                StaffPosition.objects.create(user=staff_user, position_id=pid)

        return staff_user


