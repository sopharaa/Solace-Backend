import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


def create_and_send_notification(
    user,
    message,
    notification_type=Notification.Type.COMMENT,
    comment=None,
    request_obj=None,
    confession=None,
):
    """Create a Notification record and push it to the user via WebSocket."""
    notification = Notification.objects.create(
        user=user,
        message=message,
        type=notification_type,
        comment=comment,
        request=request_obj,
        confession=confession,
    )

    # Serialize for the WebSocket payload
    serialized = NotificationSerializer(notification).data

    # Send to user's personal notification group
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'send_notification',
                    'notification': serialized,
                },
            )
        except Exception as e:
            logger.error(f'Failed to send WebSocket notification: {e}')

    return notification


def broadcast_confession_event(confession_uuid, event_type, data):
    """Broadcast an event (new_comment, delete_comment, new_message)
    to all WebSocket clients viewing a specific confession."""
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'confession_{confession_uuid}',
                {
                    'type': event_type,
                    **data,
                },
            )
        except Exception as e:
            logger.error(f'Failed to broadcast confession event: {e}')
