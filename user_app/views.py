from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer, GoogleLoginSerializer
from .models import BlacklistedAccessToken, User
import requests as http_requests

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
@permission_classes([AllowAny])
def google_auth_callback(request):
    """Exchange a Google OAuth authorization code for user info and return JWT tokens.

    This endpoint is used by the redirect-based OAuth flow:
    1. Frontend redirects user to Google's consent screen
    2. Google redirects back to /auth/callback with an authorization code
    3. Frontend sends the code here
    4. Backend exchanges it with Google for tokens + user info
    5. Returns Solace JWT tokens + user data
    """
    code = request.data.get('code')
    redirect_uri = request.data.get('redirect_uri')
    if not code or not redirect_uri:
        return Response({'error': 'Authorization code and redirect_uri are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Exchange the authorization code for tokens with Google
    token_resp = http_requests.post('https://oauth2.googleapis.com/token', data={
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    })

    if token_resp.status_code != 200:
        return Response({'error': 'Failed to exchange authorization code with Google.'},
                        status=status.HTTP_400_BAD_REQUEST)

    token_data = token_resp.json()
    id_token_str = token_data.get('id_token')
    if not id_token_str:
        return Response({'error': 'No ID token received from Google.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Verify the ID token via Google's tokeninfo endpoint (same as GoogleLoginSerializer)
    verify_resp = http_requests.get(
        'https://oauth2.googleapis.com/tokeninfo',
        params={'id_token': id_token_str},
    )
    if verify_resp.status_code != 200:
        return Response({'error': 'Invalid ID token from Google.'},
                        status=status.HTTP_400_BAD_REQUEST)

    userinfo = verify_resp.json()
    email = userinfo.get('email')
    if not email:
        return Response({'error': 'Could not retrieve email from Google.'},
                        status=status.HTTP_400_BAD_REQUEST)

    google_id = userinfo.get('sub', '')

    # Find or create user (same logic as GoogleLoginSerializer.create)

    user = User.objects.filter(email=email).first()
    if user:
        if user.status == User.Status.BANNED:
            return Response({'error': 'This account has been banned.'}, status=status.HTTP_403_FORBIDDEN)
        if user.deleted_at is not None:
            # Anonymize old record's unique fields so a new record can be created
            deleted_ts = int(user.deleted_at.timestamp())
            user.email = f"{user.email}_deleted_{deleted_ts}"
            if user.provider_id:
                user.provider_id = f"{user.provider_id}_deleted_{deleted_ts}"
            user.save(update_fields=['email', 'provider_id', 'updated_at'])

            # Create a brand-new user record
            user = User.objects.create_user(
                email=email,
                name=userinfo.get('name', ''),
                provider_id=google_id,
                avatar_url=userinfo.get('picture', ''),
                status=User.Status.APPROVED,
            )
        else:
            if not user.provider_id:
                user.provider_id = google_id
                user.save(update_fields=['provider_id'])
    else:
        user = User.objects.create_user(
            email=email,
            name=userinfo.get('name', ''),
            provider_id=google_id,
            avatar_url=userinfo.get('picture', ''),
            status=User.Status.APPROVED,
        )

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
    users = User.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return or update the currently authenticated user's profile."""
    user = request.user
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        if 'name' in request.data:
            user.name = request.data['name']
            
        if 'password' in request.data:
            current_password = request.data.get('current_password')
            if not current_password or not user.check_password(current_password):
                return Response({'error': 'Invalid current password.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(request.data['password'])
            
        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, uuid):
    user = get_object_or_404(User, uuid=uuid, deleted_at__isnull=True)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'PATCH':
        if request.user.promoted_by == user:
            return Response({'error': 'You cannot perform actions on the admin who promoted you.'}, status=status.HTTP_403_FORBIDDEN)
            
        if 'role_id' in request.data or 'position_ids' in request.data or request.data.get('status') == 'BANNED':
            admin_password = request.data.get('admin_password')
            if not admin_password or not request.user.check_password(admin_password):
                return Response({'error': 'Invalid admin password. Verification failed.'}, status=status.HTTP_403_FORBIDDEN)
                
        old_status = user.status
        if 'status' in request.data:
            new_status = request.data['status'].upper()
            user.status = new_status
            if new_status == 'BANNED':
                user.is_active = False
            elif new_status == 'APPROVED':
                user.is_active = True

            if old_status.upper() == 'PENDING' and new_status in ['APPROVED', 'REJECTED']:
                from mail_app.utils import send_user_status_email
                send_user_status_email(user, new_status)

        if 'role_id' in request.data:
            from role_app.models import Role
            role = get_object_or_404(Role, uuid=request.data['role_id'])
            
            if role.name.upper() == 'ADMIN' and request.user.promoted_by is not None:
                return Response({'error': 'Promoted admins do not have permission to grant the Admin role.'}, status=status.HTTP_403_FORBIDDEN)
                
            user.role = role
            user.promoted_by = request.user
            
        if 'temp_password' in request.data:
            user.set_password(request.data['temp_password'])
            
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
        if request.user.promoted_by == user:
            return Response({'error': 'You cannot perform actions on the admin who promoted you.'}, status=status.HTTP_403_FORBIDDEN)
            
        admin_password = request.data.get('admin_password')
        if not admin_password or not request.user.check_password(admin_password):
            return Response({'error': 'Invalid admin password. Verification failed.'}, status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone
        from position_app.models import StaffPosition

        # Soft-delete and reset identity so the user starts fresh on next login
        user.deleted_at = timezone.now()
        user.role = None
        user.status = User.Status.APPROVED
        user.is_active = False
        user.save(update_fields=['deleted_at', 'role', 'status', 'is_active', 'updated_at'])

        # Remove all position assignments
        StaffPosition.objects.filter(user=user).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_verify_password(request):
    """Verify the current admin user's password (e.g. for revealing anonymous identities)."""
    user = request.user
    if not user.role or user.role.name != 'ADMIN':
        return Response({'error': 'Only admins can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

    password = request.data.get('password', '')
    if not password or not user.check_password(password):
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'verified': True}, status=status.HTTP_200_OK)