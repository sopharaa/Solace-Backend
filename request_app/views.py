from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Request
from .serializers import RequestSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_requests(request):
    requests = Request.objects.all().order_by('-created_at')
    serializer = RequestSerializer(requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_request(request):
    serializer = RequestSerializer(data=request.data)
    if serializer.is_valid():
        req = serializer.save(user_id=request.user)
        
        # Send notifications to all admins
        from user_app.models import User
        from notification_app.utils import create_and_send_notification
        from notification_app.models import Notification as NotifModel
        
        admins = User.objects.filter(role__name='ADMIN', deleted_at__isnull=True)
        for admin in admins:
            create_and_send_notification(
                user=admin,
                message=f'User {request.user.name} has submitted a new change request.',
                notification_type=NotifModel.Type.REQUEST_CHANGE,
                request_obj=req,
            )
            
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def respond_request(request, uuid):
    try:
        req = Request.objects.get(uuid=uuid)
    except Request.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        
    req_status = request.data.get('status')
    if req_status not in [Request.Status.APPROVED, Request.Status.REJECTED]:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
    req.status = req_status
    req.save()

    # Send notification to the requesting user about approval/rejection
    from notification_app.utils import create_and_send_notification
    from notification_app.models import Notification as NotifModel

    status_label = 'approved' if req_status == Request.Status.APPROVED else 'rejected'
    create_and_send_notification(
        user=req.user_id,  # The user who made the request
        message=f'Your request has been {status_label} by admin.',
        notification_type=NotifModel.Type.REQUEST_CHANGE,
        request_obj=req,
    )

    # Send email notification about approval/rejection
    from mail_app.utils import send_request_status_email
    send_request_status_email(req, status_label)
    
    serializer = RequestSerializer(req)
    return Response(serializer.data, status=status.HTTP_200_OK)
