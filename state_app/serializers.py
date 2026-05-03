from rest_framework import serializers
from .models import State


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'uuid', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']

    def validate_name(self, value):
        qs = State.objects.filter(name__iexact=value, is_active=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A state with this name already exists.')
        return value
