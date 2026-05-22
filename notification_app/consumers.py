import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for user-specific notifications."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user:
            await self.close(code=4001)
            return

        # User-specific notification group
        self.user_group = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Role-based group
        role_name = await self._get_role_name()
        if role_name:
            self.role_group = f'{role_name.lower()}_notifications'
            await self.channel_layer.group_add(self.role_group, self.channel_name)
        else:
            self.role_group = None

        await self.accept()

        # Send unread count on connect
        unread_count = await self._get_unread_count()
        await self.send_json({
            'type': 'unread_count',
            'count': unread_count,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, 'role_group') and self.role_group:
            await self.channel_layer.group_discard(self.role_group, self.channel_name)

    async def receive_json(self, content):
        """Handle messages from the client (mark_read, mark_all_read)."""
        action = content.get('action')

        if action == 'mark_read':
            uuid = content.get('uuid')
            if uuid:
                await self._mark_read(uuid)
                unread_count = await self._get_unread_count()
                await self.send_json({'type': 'unread_count', 'count': unread_count})

        elif action == 'mark_all_read':
            await self._mark_all_read()
            await self.send_json({'type': 'unread_count', 'count': 0})

    # ── Group message handlers ──

    async def send_notification(self, event):
        """Called when a notification is sent to this user's group."""
        await self.send_json({
            'type': 'new_notification',
            'notification': event['notification'],
        })

    # ── DB helpers ──

    @database_sync_to_async
    def _get_role_name(self):
        if self.user and self.user.role:
            return self.user.role.name
        return None

    @database_sync_to_async
    def _get_unread_count(self):
        return Notification.objects.filter(
            user=self.user,
            status=Notification.Status.UNREAD,
            deleted_at__isnull=True,
        ).count()

    @database_sync_to_async
    def _mark_read(self, uuid):
        Notification.objects.filter(
            user=self.user, uuid=uuid, deleted_at__isnull=True
        ).update(status=Notification.Status.READ)

    @database_sync_to_async
    def _mark_all_read(self):
        Notification.objects.filter(
            user=self.user,
            status=Notification.Status.UNREAD,
            deleted_at__isnull=True,
        ).update(status=Notification.Status.READ)


class ConfessionConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time updates within a confession
    (new comments, new messages, deleted comments)."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user:
            await self.close(code=4001)
            return

        self.confession_uuid = self.scope['url_route']['kwargs']['uuid']
        self.confession_group = f'confession_{self.confession_uuid}'
        await self.channel_layer.group_add(self.confession_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'confession_group'):
            await self.channel_layer.group_discard(
                self.confession_group, self.channel_name
            )

    # ── Group message handlers ──

    async def new_comment(self, event):
        """Broadcast new comment to all viewers of this confession."""
        await self.send_json({
            'type': 'new_comment',
            'comment': event['comment'],
        })

    async def delete_comment(self, event):
        """Broadcast comment deletion."""
        await self.send_json({
            'type': 'delete_comment',
            'comment_uuid': event['comment_uuid'],
        })

    async def new_message(self, event):
        """Broadcast new message (student or AI) to all viewers."""
        await self.send_json({
            'type': 'new_message',
            'message': event['message'],
        })
