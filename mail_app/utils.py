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


def send_first_comment_email(recipient_email, recipient_name, confession_title, commenter_name, comment_content, confession_uuid):
    """
    Send an email to the confession owner when a staff member
    posts the FIRST comment on their confession (Asynchronous).
    """
    _run_async(
        _send_first_comment_email_sync,
        recipient_email,
        recipient_name,
        confession_title,
        commenter_name,
        comment_content,
        confession_uuid
    )


def _send_first_comment_email_sync(recipient_email, recipient_name, confession_title, commenter_name, comment_content, confession_uuid):
    if not recipient_email:
        logger.warning('No email provided, skipping first-comment email.')
        return

    subject = f'First Comment on Your Confession — "{confession_title}"'

    context = {
        'user_name': recipient_name,
        'confession_title': confession_title,
        'commenter_name': commenter_name,
        'comment_content': comment_content,
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
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'First-comment email sent to {recipient_email} for confession {confession_uuid}')
    except Exception as e:
        logger.error(f'Failed to send first-comment email to {recipient_email}: {e}')


def send_request_status_email(user_email, user_name, request_uuid, request_description, new_status):
    """
    Send an email to the user when their request is approved or rejected by admin (Asynchronous).
    """
    _run_async(
        _send_request_status_email_sync,
        user_email,
        user_name,
        request_uuid,
        request_description,
        new_status
    )


def _send_request_status_email_sync(user_email, user_name, request_uuid, request_description, new_status):
    if not user_email:
        logger.warning('No email provided, skipping request-status email.')
        return

    status_label = new_status.lower()  # 'approved' or 'rejected'
    subject = f'Your Request Has Been {status_label.capitalize()}'

    context = {
        'user_name': user_name,
        'request_uuid': str(request_uuid),
        'request_description': request_description,
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
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Request-status email ({status_label}) sent to {user_email}')
    except Exception as e:
        logger.error(f'Failed to send request-status email to {user_email}: {e}')


def send_user_status_email(user_email, user_name, new_status):
    """
    Send an email to the user when their account registration/status is approved or rejected by admin (Asynchronous).
    """
    _run_async(_send_user_status_email_sync, user_email, user_name, new_status)


def _send_user_status_email_sync(user_email, user_name, new_status):
    if not user_email:
        logger.warning('No email provided, skipping user-status email.')
        return

    status_label = new_status.lower()  # 'approved' or 'rejected'
    subject = f'Your Account Has Been {status_label.capitalize()}'

    context = {
        'user_name': user_name,
        'status_label': status_label,
        'site_name': settings.EMAIL_SITE_NAME,
        'frontend_url': settings.EMAIL_FRONTEND_URL,
    }

    html_message = render_to_string('mail_app/user_status.html', context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'User-status email ({status_label}) sent to {user_email}')
    except Exception as e:
        logger.error(f'Failed to send user-status email to {user_email}: {e}')
