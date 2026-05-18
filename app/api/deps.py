from typing import Any
from django.http import HttpRequest
from ninja.security import HttpBearer
from app.core.security import decode_token

class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> Any:
        try:
            payload = decode_token(token)
            # In Django Ninja, the return value of authenticate is assigned to request.auth
            return payload
        except Exception:
            return None
