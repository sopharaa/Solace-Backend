from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from user_app.models import User
from user_app.serializers import UserSerializer
from .serializers import SelectRoleSerializer, ReviewRoleRequestSerializer
from .permissions import IsAdmin


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
        role__name='STAFF', status=User.Status.PENDING
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


