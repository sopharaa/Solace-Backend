from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from user_app.models import User
from user_app.serializers import UserSerializer
from .serializers import SelectRoleSerializer, ReviewRoleRequestSerializer, RoleSerializer
from .models import Role
from .permissions import IsAdmin
from django.db.models import Count, Q


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def list_or_create_role(request):
    if request.method == 'GET':
        roles = Role.objects.annotate(
            user_count=Count('users', filter=Q(users__status__in=['APPROVED', 'ACTIVE'], users__deleted_at__isnull=True))
        ).filter(deleted_at__isnull=True).order_by('name')
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — restore soft-deleted record if same name exists, otherwise create new
    name = request.data.get('name', '').strip()
    existing = Role.objects.filter(name__iexact=name, deleted_at__isnull=False).first()
    if existing:
        serializer = RoleSerializer(existing, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(deleted_at=None)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer = RoleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAdmin])
def role_detail(request, pk):
    try:
        role = Role.objects.annotate(
            user_count=Count('users', filter=Q(users__status__in=['APPROVED', 'ACTIVE'], users__deleted_at__isnull=True))
        ).get(pk=pk, deleted_at__isnull=True)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = RoleSerializer(role)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ('PUT', 'PATCH'):
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE (soft)
    role.deleted_at = timezone.now()
    role.save(update_fields=['deleted_at'])
    return Response({'message': 'Role deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_role(request):
    serializer = SelectRoleSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    message = (
        'Role assigned successfully'
        if user.status == User.Status.APPROVED
        else 'Role request submitted, waiting for admin approval'
    )

    return Response({
        'message': message,
        'user': UserSerializer(user).data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_role_requests(request):
    pending_users = User.objects.filter(
        role__name='STAFF', status__in=[User.Status.PENDING, User.Status.REJECTED, User.Status.APPROVED]
    ).select_related('role').order_by('-created_at')

    serializer = UserSerializer(pending_users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAdmin])
def review_role_request(request, pk):
    try:
        role_user = User.objects.select_related('role').get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if role_user.role is None or role_user.role.name != 'STAFF':
        return Response({'error': 'User is not a staff member'}, status=status.HTTP_400_BAD_REQUEST)

    if role_user.status != User.Status.PENDING:
        return Response(
            {'error': f'User has already been {role_user.status.lower()}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReviewRoleRequestSerializer(
        data=request.data,
        context={'role_user': role_user},
    )
    serializer.is_valid(raise_exception=True)
    updated_user = serializer.save()

    return Response({
        'message': f'Role request {updated_user.status.lower()}',
        'user': UserSerializer(updated_user).data,
    }, status=status.HTTP_200_OK)
