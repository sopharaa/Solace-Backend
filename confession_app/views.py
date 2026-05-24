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
    StaffConfessionListSerializer,
    StaffConfessionDetailSerializer,
    StudentCommentListSerializer,
    StudentCommentDetailSerializer,
    AdminConfessionListSerializer,
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
import threading
from django.db import close_old_connections

def _generate_ai_title_and_response_bg(confession_id, user_id, message_content, states, positions, is_anonymous):
    try:
        from .models import Confession
        from user_app.models import User
        from message_app.models import Message
        from solace_backend.ai_service import generate_supportive_response, generate_confession_title
        
        confession = Confession.objects.get(id=confession_id)
        user = User.objects.get(id=user_id)
        
        # 1. Generate title in background
        title = 'New Confession'
        try:
            title = generate_confession_title(message_content)
            confession.title = title
            confession.save()
        except Exception as e:
            logger.error(f"Error generating AI title in background: {e}")
            
        # 2. Notify staff members with the generated title
        from notification_app.utils import create_and_send_notification
        from notification_app.models import Notification as NotifModel
        from position_app.models import StaffPosition
        
        position_ids = ConfessionPosition.objects.filter(
            confession=confession, deleted_at__isnull=True
        ).values_list('position_id', flat=True)
        
        if position_ids:
            staff_user_ids = StaffPosition.objects.filter(
                position_id__in=position_ids, deleted_at__isnull=True
            ).values_list('user_id', flat=True).distinct()
            
            from user_app.models import User as UserAppModel
            staff_users = UserAppModel.objects.filter(id__in=staff_user_ids, deleted_at__isnull=True)
            
            for staff_user in staff_users:
                create_and_send_notification(
                    user=staff_user,
                    message=f'A student needs support in your area: "{title}"',
                    notification_type=NotifModel.Type.REQUEST_CONNECT,
                    confession=confession,
                )
        
        # 3. Generate AI response in background
        ctx = _get_user_context(user)
        conversation_history = [{'role': 'user', 'content': message_content}]
        try:
            ai_text = generate_supportive_response(
                user_name=ctx['user_name'],
                user_role=ctx['user_role'],
                user_positions=ctx['user_positions'],
                confession_states=states,
                confession_positions=positions,
                is_anonymous=is_anonymous,
                conversation_history=conversation_history,
            )
        except Exception:
            ai_text = "I hear you. Thank you for sharing. I'm here to support you."
            
        Message.objects.create(
            confession=confession,
            content=ai_text,
            type=Message.MessageType.AI,
        )
    except Exception as e:
        logger.error(f"Error in background AI processing: {e}")
    finally:
        close_old_connections()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def confession_list_create(request):
    """
    GET  → list current user's confessions (for sidebar).
    POST → create a new confession with first message + AI response.
    """
    user = request.user

    if request.method == 'GET':
        qs = (
            Confession.objects.filter(user=user, deleted_at__isnull=True, is_archived=False)
            .order_by('-updated_at')
        )

        cursor = request.query_params.get('cursor')
        if cursor:
            from django.utils.dateparse import parse_datetime
            cursor_dt = parse_datetime(cursor)
            if cursor_dt:
                qs = qs.filter(updated_at__lt=cursor_dt)

        limit = min(int(request.query_params.get('limit', 10)), 100)
        page = list(qs[:limit + 1])
        has_next = len(page) > limit
        page = page[:limit]

        serializer = ConfessionListSerializer(page, many=True)
        return Response({
            'results': serializer.data,
            'has_next': has_next,
            'next_cursor': page[-1].updated_at.isoformat() if has_next and page else None,
        }, status=status.HTTP_200_OK)

    # POST — create confession
    ser = CreateConfessionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    # 1. Create the confession instantly with default/placeholder title
    confession = Confession.objects.create(
        user=user,
        title='New Confession',
        is_anonymous=data.get('is_anonymous', False),
    )

    # 2. Attach confession states
    states = data.get('states', [])
    for state_name in states:
        state_obj = State.objects.filter(name=state_name, is_active=True, deleted_at__isnull=True).first()
        if state_obj:
            ConfessionState.objects.create(confession=confession, state=state_obj)

    # 3. Attach confession positions
    positions = data.get('positions', [])
    for pos_name in positions:
        pos_obj = Position.objects.filter(name=pos_name, is_active=True, deleted_at__isnull=True).first()
        if pos_obj:
            ConfessionPosition.objects.create(confession=confession, position=pos_obj)

    # 4. Save the student's first message instantly
    Message.objects.create(
        confession=confession,
        content=data['message'],
        type=Message.MessageType.STUDENT,
    )

    # 5. Start background thread to generate AI title, notify staff, and generate supportive AI response
    thread = threading.Thread(
        target=_generate_ai_title_and_response_bg,
        args=(confession.id, user.id, data['message'], states, positions, data.get('is_anonymous', False))
    )
    thread.daemon = True
    thread.start()

    # 6. Return full confession with messages instantly
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


# ── Staff views ──────────────────────────────────────────────────

PAGE_SIZE = 20


def _get_staff_position_ids(user):
    """Return the set of position IDs assigned to this staff user."""
    from position_app.models import StaffPosition
    return set(
        StaffPosition.objects.filter(user=user, deleted_at__isnull=True)
        .values_list('position_id', flat=True)
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_confession_list(request):
    """
    List confessions visible to this staff member.
    - Filtered by position: only confessions whose positions overlap
      with the staff member's assigned positions.
    - Paginated: ?cursor=<ISO datetime>&limit=<int>
    """
    user = request.user
    if user.role and user.role.name == 'Student':
        return Response(
            {'error': 'Students cannot access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    staff_pos_ids = _get_staff_position_ids(user)

    # Base queryset: non-deleted, non-archived confessions
    qs = (
        Confession.objects.filter(deleted_at__isnull=True, is_archived=False)
        .select_related('user', 'user__role')
        .order_by('-updated_at')
    )

    # Position-based filtering: only show confessions that share at
    # least one position with the staff member.
    if staff_pos_ids:
        confession_ids_with_match = (
            ConfessionPosition.objects.filter(
                deleted_at__isnull=True,
                position_id__in=staff_pos_ids,
            ).values_list('confession_id', flat=True)
        )
        qs = qs.filter(id__in=confession_ids_with_match)
    else:
        # Staff has no positions assigned — show nothing
        qs = qs.none()

    # Cursor-based pagination (cursor = updated_at of the last item)
    cursor = request.query_params.get('cursor')
    if cursor:
        from django.utils.dateparse import parse_datetime
        cursor_dt = parse_datetime(cursor)
        if cursor_dt:
            qs = qs.filter(updated_at__lt=cursor_dt)

    limit = min(int(request.query_params.get('limit', PAGE_SIZE)), 100)
    page = list(qs[:limit + 1])  # Fetch one extra to know if there's a next page
    has_next = len(page) > limit
    page = page[:limit]

    serializer = StaffConfessionListSerializer(page, many=True)
    return Response({
        'results': serializer.data,
        'has_next': has_next,
        'next_cursor': page[-1].updated_at.isoformat() if has_next and page else None,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_confession_detail(request, uuid):
    """Retrieve full confession detail for staff (position-gated)."""
    user = request.user
    if user.role and user.role.name == 'Student':
        return Response(
            {'error': 'Students cannot access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        confession = Confession.objects.select_related('user', 'user__role').get(
            uuid=uuid, deleted_at__isnull=True
        )
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Check position access
    staff_pos_ids = _get_staff_position_ids(user)
    confession_pos_ids = set(
        ConfessionPosition.objects.filter(
            confession=confession, deleted_at__isnull=True
        ).values_list('position_id', flat=True)
    )
    if not staff_pos_ids.intersection(confession_pos_ids):
        return Response(
            {'error': 'You do not have access to this confession.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = StaffConfessionDetailSerializer(confession)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Student comment views ────────────────────────────────────────

STUDENT_PAGE_SIZE = 6


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_comment_list(request):
    """
    List the current student's confessions with comment summaries.
    Paginated: ?cursor=<ISO datetime>&limit=<int>
    Optional:  ?archived=true  → only archived confessions
               ?archived=false → only non-archived (default)
    """
    user = request.user
    # Only show confessions that have at least one position assigned
    # (confessions where the student chose "none" are excluded).
    confession_ids_with_positions = (
        ConfessionPosition.objects.filter(deleted_at__isnull=True)
        .values_list('confession_id', flat=True)
    )

    # Archive filter (default: non-archived)
    archived_param = request.query_params.get('archived', 'false').lower()
    show_archived = archived_param in ('true', '1', 'yes')

    qs = (
        Confession.objects.filter(
            user=user,
            deleted_at__isnull=True,
            is_archived=show_archived,
            id__in=confession_ids_with_positions,
        )
        .select_related('user', 'user__role')
        .order_by('-updated_at')
    )

    # Cursor-based pagination
    cursor = request.query_params.get('cursor')
    if cursor:
        from django.utils.dateparse import parse_datetime
        cursor_dt = parse_datetime(cursor)
        if cursor_dt:
            qs = qs.filter(updated_at__lt=cursor_dt)

    limit = min(int(request.query_params.get('limit', STUDENT_PAGE_SIZE)), 100)
    page = list(qs[:limit + 1])
    has_next = len(page) > limit
    page = page[:limit]

    serializer = StudentCommentListSerializer(page, many=True)
    return Response({
        'results': serializer.data,
        'has_next': has_next,
        'next_cursor': page[-1].updated_at.isoformat() if has_next and page else None,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_comment_detail(request, uuid):
    """
    Retrieve a single confession with its full comment thread.
    Used by /student/view-comment/[id] detail page.
    Only the owning student can access.
    """
    user = request.user
    try:
        confession = Confession.objects.select_related('user', 'user__role').get(
            uuid=uuid, user=user, deleted_at__isnull=True
        )
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = StudentCommentDetailSerializer(confession, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Admin views ──────────────────────────────────────────────────

ADMIN_PAGE_SIZE = 20


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_confession_list(request):
    """
    List ALL confessions for admin oversight.
    Paginated: ?cursor=<ISO datetime>&limit=<int>
    Optional:  ?search=<query>
    Only admins can access.
    """
    user = request.user
    if not user.role or user.role.name != 'ADMIN':
        return Response(
            {'error': 'Only admins can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    base_qs = (
        Confession.objects.filter(deleted_at__isnull=True)
        .select_related('user', 'user__role')
        .order_by('-updated_at')
    )

    # Search filter
    search = request.query_params.get('search', '').strip()
    if search:
        from django.db.models import Q
        base_qs = base_qs.filter(
            Q(title__icontains=search) |
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search)
        )

    # Archived filter
    archived_filter = request.query_params.get('archived')
    if archived_filter == 'true':
        base_qs = base_qs.filter(is_archived=True)
    elif archived_filter == 'false':
        base_qs = base_qs.filter(is_archived=False)

    # Compute total counts BEFORE anonymous filter and cursor pagination
    total_count = base_qs.count()
    anonymous_count = base_qs.filter(is_anonymous=True).count()
    non_anonymous_count = total_count - anonymous_count

    # Anonymous filter
    qs = base_qs
    anon_filter = request.query_params.get('anonymous')
    if anon_filter == 'true':
        qs = qs.filter(is_anonymous=True)
    elif anon_filter == 'false':
        qs = qs.filter(is_anonymous=False)

    limit = min(int(request.query_params.get('limit', ADMIN_PAGE_SIZE)), 100)
    page_param = request.query_params.get('page')

    if page_param:
        try:
            page_num = max(1, int(page_param))
        except ValueError:
            page_num = 1
        offset = (page_num - 1) * limit
        page_items = list(qs[offset:offset + limit + 1])
        has_next = len(page_items) > limit
        page = page_items[:limit]
        next_cursor = None
    else:
        # Cursor-based pagination
        cursor = request.query_params.get('cursor')
        if cursor:
            from django.utils.dateparse import parse_datetime
            cursor_dt = parse_datetime(cursor)
            if cursor_dt:
                qs = qs.filter(updated_at__lt=cursor_dt)

        page_items = list(qs[:limit + 1])
        has_next = len(page_items) > limit
        page = page_items[:limit]
        next_cursor = page[-1].updated_at.isoformat() if has_next and page else None

    serializer = AdminConfessionListSerializer(page, many=True)
    return Response({
        'results': serializer.data,
        'has_next': has_next,
        'next_cursor': next_cursor,
        'total_count': total_count,
        'anonymous_count': anonymous_count,
        'non_anonymous_count': non_anonymous_count,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_confession_detail(request, uuid):
    """Retrieve full confession detail for admin (no position gating)."""
    user = request.user
    if not user.role or user.role.name != 'ADMIN':
        return Response(
            {'error': 'Only admins can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        confession = Confession.objects.select_related('user', 'user__role').get(
            uuid=uuid, deleted_at__isnull=True
        )
    except Confession.DoesNotExist:
        return Response({'error': 'Confession not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = StaffConfessionDetailSerializer(confession)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    """
    Get aggregated statistics for the admin dashboard.
    """
    user = request.user
    if not user.role or user.role.name != 'ADMIN':
        return Response(
            {'error': 'Only admins can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    from user_app.models import User
    from comment_app.models import Comment
    from request_app.models import Request
    from confession_app.models import Confession

    total_users = User.objects.filter(deleted_at__isnull=True).count()
    total_confessions = Confession.objects.filter(deleted_at__isnull=True).count()
    total_comments = Comment.objects.filter(deleted_at__isnull=True).count()
    pending_requests = Request.objects.filter(status='PENDING', deleted_at__isnull=True).count()
    total_sessions = total_users * 3 # Mocked sessions multiplier

    return Response({
        'total_users': total_users,
        'total_confessions': total_confessions,
        'total_comments': total_comments,
        'total_sessions': total_sessions,
        'pending_requests': pending_requests,
    }, status=status.HTTP_200_OK)
