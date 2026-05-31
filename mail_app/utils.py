import logging
import threading
from django.db import connections
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def _run_async(target, *args, **kwargs):
    """Helper to run a function in a background thread and clean up DB connections."""
    def wrapper():
        try:
            target(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in background email thread: {e}")
        finally:
            # Close database connections for this thread to avoid connection leaks
            connections.close_all()

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()


def send_first_comment_email(confession, comment, commenter_display_name):
    """
    Send an email to the confession owner when a staff member
    posts the FIRST comment on their confession (Asynchronous).
    """
    _run_async(_send_first_comment_email_sync, confession, comment, commenter_display_name)


def _send_first_comment_email_sync(confession, comment, commenter_display_name):
    recipient = confession.user
    if not recipient.email:
        logger.warning(f'No email for user {recipient.id}, skipping first-comment email.')
        return

    subject = f'New Comment on Your Confession — "{confession.title}"'

    context = {
        'user_name': recipient.name,
        'confession_title': confession.title,
        'commenter_name': commenter_display_name,
        'comment_content': comment.content,
        'site_name': settings.EMAIL_SITE_NAME,
        'frontend_url': settings.EMAIL_FRONTEND_URL,
    }

    html_message = render_to_string('mail_app/first_comment.html', context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'First-comment email sent to {recipient.email} for confession {confession.uuid}')
    except Exception as e:
        logger.error(f'Failed to send first-comment email to {recipient.email}: {e}')


def send_request_status_email(request_obj, new_status):
    """
    Send an email to the user when their request is approved or rejected by admin (Asynchronous).
    """
    _run_async(_send_request_status_email_sync, request_obj, new_status)


def _send_request_status_email_sync(request_obj, new_status):
    recipient = request_obj.user_id  # ForeignKey field named user_id
    if not recipient.email:
        logger.warning(f'No email for user {recipient.id}, skipping request-status email.')
        return

    status_label = new_status.lower()  # 'approved' or 'rejected'
    subject = f'Your Request Has Been {status_label.capitalize()}'

    context = {
        'user_name': recipient.name,
        'request_uuid': str(request_obj.uuid),
        'request_description': request_obj.description,
        'status_label': status_label,
        'site_name': settings.EMAIL_SITE_NAME,
        'frontend_url': settings.EMAIL_FRONTEND_URL,
    }

    html_message = render_to_string('mail_app/request_status.html', context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Request-status email ({status_label}) sent to {recipient.email}')
    except Exception as e:
        logger.error(f'Failed to send request-status email to {recipient.email}: {e}')

