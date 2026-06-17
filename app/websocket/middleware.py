from __future__ import annotations

from uuid import UUID
from urllib.parse import parse_qs

from app.core.security import decode_token


def _get_header(scope: dict, header_name: str) -> str | None:
    name_bytes = header_name.lower().encode()
    for k, v in scope.get("headers") or []:
        if k.lower() == name_bytes:
            try:
                return v.decode()
            except Exception:
                return None
    return None


def _get_token_from_scope(scope: dict) -> str | None:
    auth = _get_header(scope, "authorization")
    if auth:
        parts = auth.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip() or None
        return auth.strip() or None

    qs = scope.get("query_string") or b""
    try:
        query = qs.decode()
    except Exception:
        query = ""
    params = parse_qs(query)
    token_list = params.get("token") or params.get("access_token") or []
    token = token_list[0] if token_list else None
    return token or None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        token = _get_token_from_scope(scope)
        if token:
            try:
                payload = decode_token(token)
                sub = payload.get("sub")
                if sub:
                    scope["jwt"] = payload
                    scope["user_id"] = UUID(str(sub))
                    scope["role"] = payload.get("role")
            except Exception:
                pass
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)

