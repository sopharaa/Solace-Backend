from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import State
from .serializers import StateSerializer
from .permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated

# Create your views here.
@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def list_or_create_state(request):
    if request.method == 'GET':
        states = State.objects.filter(is_active=True).order_by('name')
        serializer = StateSerializer(states, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — restore soft-deleted record if same name exists, otherwise create new
    name = request.data.get('name', '').strip()
    existing = State.objects.filter(name__iexact=name, is_active=False).first()
    if existing:
        serializer = StateSerializer(existing, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(is_active=True, deleted_at=None)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer = StateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAdmin])
def state_detail(request, pk):
    try:
        state = State.objects.get(pk=pk)
    except State.DoesNotExist:
        return Response({'error': 'State not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = StateSerializer(state)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ('PUT', 'PATCH'):
        serializer = StateSerializer(state, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE (soft)
    state.is_active = False
    state.deleted_at = timezone.now()
    state.save(update_fields=['is_active', 'deleted_at'])
    return Response({'message': 'State deleted successfully'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_active_states(request):
    states = State.objects.filter(is_active=True).order_by('name')
    serializer = StateSerializer(states, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
