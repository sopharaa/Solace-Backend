from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from user_app.models import User
from user_app.serializers import UserSerializer
from .models import Position, StaffPosition
from .serializers import PositionSerializer, AssignPositionsSerializer
from .permissions import IsAdmin


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def list_or_create_position(request):
    if request.method == 'GET':
        positions = Position.objects.filter(is_active=True).order_by('name')
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — restore soft-deleted record if same name exists, otherwise create new
    name = request.data.get('name', '').strip()
    existing = Position.objects.filter(name__iexact=name, is_active=False).first()
    if existing:
        serializer = PositionSerializer(existing, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(is_active=True, deleted_at=None)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer = PositionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAdmin])
def position_detail(request, pk):
    try:
        position = Position.objects.get(pk=pk)
    except Position.DoesNotExist:
        return Response({'error': 'Position not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PositionSerializer(position)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ('PUT', 'PATCH'):
        serializer = PositionSerializer(position, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE (soft)
    position.is_active = False
    position.deleted_at = timezone.now()
    position.save(update_fields=['is_active', 'deleted_at'])
    return Response({'message': 'Position deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAdmin])
def toggle_position(request, pk):
    try:
        position = Position.objects.get(pk=pk)
    except Position.DoesNotExist:
        return Response({'error': 'Position not found'}, status=status.HTTP_404_NOT_FOUND)

    is_active = request.data.get('is_active')
    if is_active is None or not isinstance(is_active, bool):
        return Response({'error': 'is_active (boolean) is required'}, status=status.HTTP_400_BAD_REQUEST)

    position.is_active = is_active
    position.deleted_at = None if is_active else timezone.now()
    position.save(update_fields=['is_active', 'deleted_at'])

    serializer = PositionSerializer(position)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
@permission_classes([IsAdmin])
def assign_positions(request, pk):
    try:
        staff_user = User.objects.select_related('role').get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if staff_user.role is None or staff_user.role.name != 'STAFF':
        return Response({'error': 'User is not a staff member'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        return Response({
            'user': UserSerializer(staff_user).data,
        }, status=status.HTTP_200_OK)

    # PUT — replace all positions
    serializer = AssignPositionsSerializer(
        data=request.data,
        context={'staff_user': staff_user},
    )
    serializer.is_valid(raise_exception=True)
    updated_user = serializer.save()

    return Response({
        'message': 'Positions assigned successfully',
        'user': UserSerializer(updated_user).data,
    }, status=status.HTTP_200_OK)
