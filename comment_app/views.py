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

    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_delete(request, uuid):
    """Soft-delete a comment (only the author can delete their own)."""
    user = request.user
    try:
        comment = Comment.objects.get(uuid=uuid, deleted_at__isnull=True)
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)

    if comment.user != user:
        return Response(
            {'error': 'You can only delete your own comments.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    comment.deleted_at = timezone.now()
    comment.save(update_fields=['deleted_at', 'updated_at'])
    return Response(status=status.HTTP_204_NO_CONTENT)
