import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from confession_app.models import Confession
from confession_state_app.models import ConfessionState
from confession_position_app.models import ConfessionPosition
from .models import Message
from .serializers import MessageSerializer, CreateMessageSerializer
from solace_backend.ai_service import generate_supportive_response

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, uuid):
    """
    POST → send a student message to an existing confession.
    Automatically generates an AI response and returns both messages.
    """
    user = request.user

    try:
        confession = Confession.objects.get(
            uuid=uuid, user=user, deleted_at__isnull=True
        )
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    ser = CreateMessageSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    content = ser.validated_data['content']

    # Save student message
    student_msg = Message.objects.create(
        confession=confession,
        content=content,
        type=Message.MessageType.STUDENT,
    )

    # Build full conversation history (including the message just saved)
    conversation_history = _build_conversation_history(confession)

    # Get confession context
    ctx = _get_user_context(user)
    confession_states = list(
        ConfessionState.objects.filter(confession=confession, deleted_at__isnull=True)
        .values_list('state__name', flat=True)
    )
    confession_positions = list(
        ConfessionPosition.objects.filter(confession=confession, deleted_at__isnull=True)
        .values_list('position__name', flat=True)
    )

    # Generate AI response
    try:
        ai_text = generate_supportive_response(
            user_name=ctx['user_name'],
            user_role=ctx['user_role'],
            user_positions=ctx['user_positions'],
            confession_states=confession_states,
            confession_positions=confession_positions,
            is_anonymous=confession.is_anonymous,
            conversation_history=conversation_history,
        )
    except Exception:
        ai_text = "Thank you for sharing. I'm here to listen and support you."

    ai_msg = Message.objects.create(
        confession=confession,
        content=ai_text,
        type=Message.MessageType.AI,
    )

    # Update confession updated_at
    confession.save(update_fields=['updated_at'])

    # Broadcast real-time messages to all viewers of this confession
    from notification_app.utils import broadcast_confession_event
    broadcast_confession_event(
        str(confession.uuid),
        'new_message',
        {'message': MessageSerializer(student_msg).data},
    )
    broadcast_confession_event(
        str(confession.uuid),
        'new_message',
        {'message': MessageSerializer(ai_msg).data},
    )

    return Response({
        'student_message': MessageSerializer(student_msg).data,
        'ai_message': MessageSerializer(ai_msg).data,
    }, status=status.HTTP_201_CREATED)
