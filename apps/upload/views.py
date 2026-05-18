from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.security import decode_token
from apps.upload.serializers import PresignedUploadSerializer
from apps.upload.services import S3UploadConfigError, S3UploadService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JWTUser:
    id: str
    role: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return True


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request: HttpRequest) -> tuple[JWTUser, str] | None:
        auth = request.headers.get("Authorization", "")
        if not auth:
            return None

        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1].strip()
        if not token:
            return None

        try:
            payload = decode_token(token)
        except Exception:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = JWTUser(id=str(user_id), role=payload.get("role"))
        return user, token


class PresignedUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes: list[type] = []

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not getattr(request.user, "is_authenticated", False):
            return Response(
                {"success": False, "message": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = PresignedUploadSerializer(data=request.data)
        if not serializer.is_valid():
            msg = next(iter(serializer.errors.values()))[0]
            return Response(
                {"success": False, "message": str(msg)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        folder: str = data["folder"]
        file_name: str = data["file_name"]
        content_type: str = data["content_type"]

        try:
            service = S3UploadService()
            result = service.generate_presigned_upload_url(
                folder=folder,
                file_name=file_name,
                content_type=content_type,
            )
        except S3UploadConfigError as e:
            logger.error("S3 upload config error", extra={"error": str(e)})
            return Response(
                {"success": False, "message": "AWS S3 is not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Failed to generate presigned URL", extra={"user_id": getattr(request.user, "id", None)})
            return Response(
                {"success": False, "message": "Failed to generate presigned URL"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Presigned URL generated successfully",
                "data": {
                    "upload_url": result.upload_url,
                    "file_url": result.file_url,
                    "expires_in": result.expires_in,
                },
            },
            status=status.HTTP_200_OK,
        )
