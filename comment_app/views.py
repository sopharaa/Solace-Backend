from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Comment
from .serializers import CommentSerializer, CreateCommentSerializer
from confession_app.models import Confession


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comment_list_create(request, uuid):
    """
    GET  → list all comments on a confession (staff only).
    POST → create a new comment on a confession (staff only).
    """
    user = request.user
    if user.role and user.role.name == 'Student':
        return Response(
            {'error': 'Students cannot access comments.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        confession = Confession.objects.get(uuid=uuid, deleted_at__isnull=True)
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        comments = Comment.objects.filter(
            confession=confession, deleted_at__isnull=True
        ).order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — create comment
    ser = CreateCommentSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    comment = Comment.objects.create(
        confession=confession,
        user=user,
        content=data['content'],
        is_anonymous=data.get('is_anonymous', False),
    )

    # Send notification to the confession owner (student)
    from notification_app.utils import create_and_send_notification, broadcast_confession_event
    from notification_app.models import Notification as NotifModel

    confession_owner = confession.user
    if confession_owner != user:  # Don't notify yourself
        sender_display = 'Anonymous Staff' if data.get('is_anonymous', False) else user.name
        create_and_send_notification(
            user=confession_owner,
            message=f'{sender_display} commented on "{confession.title}"',
            notification_type=NotifModel.Type.COMMENT,
            comment=comment,
            confession=confession,
        )

    # Broadcast real-time comment to all viewers of this confession
    broadcast_confession_event(
        str(confession.uuid),
        'new_comment',
        {'comment': CommentSerializer(comment).data},
    )

    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_delete(request, uuid):
    """Soft-delete a comment (author can delete own, admin can delete any)."""
    user = request.user
    try:
        comment = Comment.objects.get(uuid=uuid, deleted_at__isnull=True)
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_admin = user.role and user.role.name == 'ADMIN'
    if not is_admin:
        return Response(
            {'error': 'Only administrators can delete comments.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    comment.deleted_at = timezone.now()
    comment.save(update_fields=['deleted_at', 'updated_at'])

    # Broadcast real-time deletion to all viewers
    from notification_app.utils import broadcast_confession_event
    broadcast_confession_event(
        str(comment.confession.uuid),
        'delete_comment',
        {'comment_uuid': str(comment.uuid)},
    )

    return Response(status=status.HTTP_204_NO_CONTENT)
