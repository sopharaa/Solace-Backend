import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Confession
from .serializers import (
    ConfessionListSerializer,
    ConfessionDetailSerializer,
    CreateConfessionSerializer,
)
from message_app.models import Message
from confession_state_app.models import ConfessionState
from confession_position_app.models import ConfessionPosition
from state_app.models import State
from position_app.models import Position
from solace_backend.ai_service import generate_supportive_response, generate_confession_title

logger = logging.getLogger(__name__)


def _get_user_context(user):
    """Build user context dict for AI service."""
    from position_app.models import StaffPosition
    positions = list(
        StaffPosition.objects.filter(user=user, deleted_at__isnull=True)
        .values_list('position__name', flat=True)
    )
    return {
        'user_name': user.name,
        'user_role': user.role.name if user.role else 'Student',
        'user_positions': positions,
    }


def _build_conversation_history(confession):
    """Convert DB messages to OpenRouter chat format."""
    messages = Message.objects.filter(
        confession=confession, deleted_at__isnull=True
    ).order_by('created_at')
    history = []
    for msg in messages:
        role = 'assistant' if msg.type == Message.MessageType.AI else 'user'
        history.append({'role': role, 'content': msg.content})
    return history


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def confession_list_create(request):
    """
    GET  → list current user's confessions (for sidebar).
    POST → create a new confession with first message + AI response.
    """
    user = request.user

    if request.method == 'GET':
        confessions = (
            Confession.objects.filter(user=user, deleted_at__isnull=True, is_archived=False)
            .order_by('-updated_at')
        )
        serializer = ConfessionListSerializer(confessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — create confession
    ser = CreateConfessionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    # 1. Generate AI title from the first message
    try:
        title = generate_confession_title(data['message'])
    except Exception:
        title = 'New Confession'

    # 2. Create the confession
    confession = Confession.objects.create(
        user=user,
        title=title,
        is_anonymous=data.get('is_anonymous', False),
    )

    # 3. Attach confession states
    for state_name in data.get('states', []):
        state_obj = State.objects.filter(name=state_name, is_active=True, deleted_at__isnull=True).first()
        if state_obj:
            ConfessionState.objects.create(confession=confession, state=state_obj)

    # 4. Attach confession positions
    for pos_name in data.get('positions', []):
        pos_obj = Position.objects.filter(name=pos_name, is_active=True, deleted_at__isnull=True).first()
        if pos_obj:
            ConfessionPosition.objects.create(confession=confession, position=pos_obj)

    # 5. Save the student's first message
    Message.objects.create(
        confession=confession,
        content=data['message'],
        type=Message.MessageType.STUDENT,
    )

    # 6. Generate AI response
    ctx = _get_user_context(user)
    confession_states = list(
        ConfessionState.objects.filter(confession=confession, deleted_at__isnull=True)
        .values_list('state__name', flat=True)
    )
    confession_positions = list(
        ConfessionPosition.objects.filter(confession=confession, deleted_at__isnull=True)
        .values_list('position__name', flat=True)
    )

    conversation_history = [{'role': 'user', 'content': data['message']}]
    try:
        ai_text = generate_supportive_response(
            user_name=ctx['user_name'],
            user_role=ctx['user_role'],
            user_positions=ctx['user_positions'],
            confession_states=confession_states,
            confession_positions=confession_positions,
            is_anonymous=data.get('is_anonymous', False),
            conversation_history=conversation_history,
        )
    except Exception:
        ai_text = "I hear you. Thank you for sharing. I'm here to support you."

    Message.objects.create(
        confession=confession,
        content=ai_text,
        type=Message.MessageType.AI,
    )

    # Return full confession with messages
    result = ConfessionDetailSerializer(confession).data
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def confession_detail(request, uuid):
    """
    GET    → retrieve a confession with all messages.
    PATCH  → update title / archive.
    DELETE → soft-delete.
    """
    try:
        confession = Confession.objects.get(
            uuid=uuid, user=request.user, deleted_at__isnull=True
        )
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ConfessionDetailSerializer(confession)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        if 'title' in request.data:
            confession.title = request.data['title']
        if 'is_archived' in request.data:
            confession.is_archived = request.data['is_archived']
            if request.data['is_archived']:
                confession.archived_at = timezone.now()
            else:
                confession.archived_at = None
        confession.save()
        serializer = ConfessionDetailSerializer(confession)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        confession.deleted_at = timezone.now()
        confession.save(update_fields=['deleted_at', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
