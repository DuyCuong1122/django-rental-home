from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qs, urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from apps.upload.serializers import CONTENT_TYPE_TO_EXT


logger = logging.getLogger(__name__)


class S3UploadConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class PresignedUploadResult:
    upload_url: str
    file_url: str
    expires_in: int
    object_key: str


class S3UploadService:
    _DEFAULT_EXPIRES_IN: Final[int] = 3600

    def __init__(self) -> None:
        self._aws_access_key_id = getattr(settings, "AWS_ACCESS_KEY_ID", "") or ""
        self._aws_secret_access_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or ""
        self._bucket_name = getattr(settings, "AWS_BUCKET_NAME", "") or ""
        self._region = (getattr(settings, "AWS_REGION", "") or "").strip()

        if not self._bucket_name:
            raise S3UploadConfigError("AWS_BUCKET_NAME is not configured")

        if not self._region:
            raise S3UploadConfigError("AWS_REGION is not configured")

        if not self._aws_access_key_id or not self._aws_secret_access_key:
            raise S3UploadConfigError("AWS credentials are not configured")

        self._s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    def generate_presigned_upload_url(self, *, folder: str, file_name: str, content_type: str) -> PresignedUploadResult:
        ext = CONTENT_TYPE_TO_EXT.get(content_type)
        if not ext:
            raise ValueError("Invalid file type")

        ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        object_key = f"{folder}/{ts}_{uuid.uuid4().hex}.{ext}"

        params = {
            "Bucket": self._bucket_name,
            "Key": object_key,
            "ContentType": content_type,
        }

        try:
            upload_url = self._s3_client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=self._DEFAULT_EXPIRES_IN,
                HttpMethod="PUT",
            )
        except (ClientError, BotoCoreError) as e:
            logger.exception("Failed to generate presigned URL", extra={"folder": folder, "content_type": content_type})
            raise RuntimeError("Failed to generate presigned URL") from e

        upload_url_base = upload_url.split("?", 1)[0]
        parsed = urlparse(upload_url)
        signed_headers = ""
        if parsed.query:
            q = parse_qs(parsed.query)
            signed_headers = (q.get("X-Amz-SignedHeaders") or [""])[0]
        logger.info(
            "Generated S3 presigned upload URL",
            extra={
                "aws_region": self._region,
                "bucket": self._bucket_name,
                "upload_url": upload_url_base,
                "upload_host": parsed.netloc,
                "signed_headers": signed_headers,
            },
        )
        if signed_headers and "x-amz-acl" in signed_headers.lower().split(";"):
            logger.warning(
                "S3 presigned URL includes x-amz-acl in SignedHeaders",
                extra={"aws_region": self._region, "bucket": self._bucket_name, "signed_headers": signed_headers},
            )
        expected_host_prefix = f"{self._bucket_name}.s3.{self._region}.amazonaws.com"
        if parsed.netloc and parsed.netloc != expected_host_prefix:
            logger.warning(
                "S3 presigned URL host does not match configured AWS_REGION",
                extra={
                    "aws_region": self._region,
                    "bucket": self._bucket_name,
                    "expected_host": expected_host_prefix,
                    "actual_host": parsed.netloc,
                },
            )

        file_url = self._build_file_url(object_key)
        return PresignedUploadResult(
            upload_url=upload_url,
            file_url=file_url,
            expires_in=self._DEFAULT_EXPIRES_IN,
            object_key=object_key,
        )

    def _build_file_url(self, object_key: str) -> str:
        return f"https://{self._bucket_name}.s3.{self._region}.amazonaws.com/{object_key}"
