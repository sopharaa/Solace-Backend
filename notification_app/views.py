from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """List notifications for the current user, newest first."""
    qs = Notification.objects.filter(
        user=request.user,
        deleted_at__isnull=True,
    ).select_related('comment', 'request', 'confession').order_by('-created_at')[:50]

    serializer = NotificationSerializer(qs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_read(request, uuid):
    """Mark a single notification as read."""
    try:
        notification = Notification.objects.get(
            uuid=uuid, user=request.user, deleted_at__isnull=True
        )
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    notification.status = Notification.Status.READ
    notification.save(update_fields=['status', 'updated_at'])
    return Response(NotificationSerializer(notification).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all unread notifications as read for the current user."""
    Notification.objects.filter(
        user=request.user,
        status=Notification.Status.UNREAD,
        deleted_at__isnull=True,
    ).update(status=Notification.Status.READ, updated_at=timezone.now())
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Get the count of unread notifications."""
    count = Notification.objects.filter(
        user=request.user,
        status=Notification.Status.UNREAD,
        deleted_at__isnull=True,
    ).count()
    return Response({'count': count})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, uuid):
    """Soft-delete a notification."""
    try:
        notification = Notification.objects.get(
            uuid=uuid, user=request.user, deleted_at__isnull=True
        )
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    notification.deleted_at = timezone.now()
    notification.save(update_fields=['deleted_at', 'updated_at'])
    return Response(status=status.HTTP_204_NO_CONTENT)
