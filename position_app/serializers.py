from django.utils import timezone
from rest_framework import serializers
from .models import Position, StaffPosition


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        # Exclude the current instance when updating
        qs = Position.objects.filter(name__iexact=value, is_active=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A position with this name already exists.')
        return value


class AssignPositionsSerializer(serializers.Serializer):
    position_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )

    def validate_position_ids(self, value):
        positions = Position.objects.filter(id__in=value, is_active=True)
        if len(positions) != len(value):
            found_ids = set(positions.values_list('id', flat=True))
            invalid_ids = [pid for pid in value if pid not in found_ids]
            raise serializers.ValidationError(f'Invalid or inactive position IDs: {invalid_ids}')
        return value

    def save(self):
        staff_user = self.context['staff_user']
        new_ids = set(self.validated_data['position_ids'])

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


