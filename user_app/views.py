from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer, GoogleLoginSerializer
from .models import BlacklistedAccessToken, User

def _build_token_pair(user):
    """Return a dict with access and refresh JWT strings for the given user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data['user']

    return Response({
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'tokens': _build_token_pair(user),
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    serializer = GoogleLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    return Response({
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'tokens': _build_token_pair(user),
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    jti = request.auth.get('jti')
    if not jti:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    BlacklistedAccessToken.objects.get_or_create(jti=jti)

    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    users = User.objects.all().order_by('-created_at')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the currently authenticated user's profile."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, uuid):
    user = get_object_or_404(User, uuid=uuid, deleted_at__isnull=True)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'PATCH':
        if 'role_id' in request.data or 'position_ids' in request.data or request.data.get('status') == 'BANNED':
            admin_password = request.data.get('admin_password')
            if not admin_password or not request.user.check_password(admin_password):
                return Response({'error': 'Invalid admin password. Verification failed.'}, status=status.HTTP_403_FORBIDDEN)
                
        if 'status' in request.data:
            user.status = request.data['status'].upper()
        if 'role_id' in request.data:
            from role_app.models import Role
            role = get_object_or_404(Role, uuid=request.data['role_id'])
            user.role = role
        user.save()
        
        if 'position_ids' in request.data:
            from position_app.models import StaffPosition, Position
            StaffPosition.objects.filter(user=user).delete()
            for pos_id in request.data['position_ids']:
                pos = get_object_or_404(Position, uuid=pos_id)
                StaffPosition.objects.create(user=user, position=pos)
                
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'DELETE':
        admin_password = request.data.get('admin_password')
        if not admin_password or not request.user.check_password(admin_password):
            return Response({'error': 'Invalid admin password. Verification failed.'}, status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone
        from position_app.models import StaffPosition

        # Soft-delete and reset identity so the user starts fresh on next login
        user.deleted_at = timezone.now()
        user.role = None
        user.status = User.Status.APPROVED
        user.save(update_fields=['deleted_at', 'role', 'status', 'updated_at'])

        # Remove all position assignments
        StaffPosition.objects.filter(user=user).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)