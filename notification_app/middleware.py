import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from user_app.models import User

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate a JWT access token and return the corresponding user."""
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return User.objects.get(id=user_id)
    except (TokenError, User.DoesNotExist, KeyError) as e:
        logger.warning(f'WebSocket auth failed: {e}')
        return None


class JWTAuthMiddleware(BaseMiddleware):
    """Custom middleware that authenticates WebSocket connections via JWT
    token passed as a query parameter."""

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        token_list = params.get('token', [])

        if token_list:
            user = await get_user_from_token(token_list[0])
            scope['user'] = user
        else:
            scope['user'] = None

        return await super().__call__(scope, receive, send)
