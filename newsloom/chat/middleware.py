from urllib.parse import parse_qs

from django.contrib.auth.models import User, AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user_by_token(key: str) -> User | AnonymousUser:
    try:
        return Token.objects.get(key=key).user
    except Token.DoesNotExist:
        return AnonymousUser()


def get_token_from_query_string(scope) -> str | None:
    query_string = scope.get('query_string', '').decode('utf-8')
    if query_string:
        qs = parse_qs(query_string)
        if 'token' in qs:
            return qs['token'][0]
    return None


def get_token_from_headers(scope) -> str | None:
    headers = scope.get('headers')
    if headers:
        for name, value in scope.get("headers", []):
            if name == b'authorization':
                return value.decode().lower().replace('token', '').strip()
    return None


class AuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        for cb in (get_token_from_query_string, get_token_from_headers):
            token = cb(scope)
            if token:
                break
        scope['user'] = await get_user_by_token(token)
        return await super().__call__(scope, receive, send) 