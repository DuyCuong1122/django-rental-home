from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from rest_framework import serializers


ALLOWED_FOLDERS: Final[set[str]] = {"avatars", "rooms", "chat"}
ALLOWED_CONTENT_TYPES: Final[set[str]] = {"image/jpeg", "image/png", "image/webp"}

CONTENT_TYPE_TO_EXT: Final[dict[str, str]] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class PresignedUploadSerializer(serializers.Serializer):
    folder = serializers.CharField()
    file_name = serializers.CharField()
    content_type = serializers.CharField()

    def validate_folder(self, value: str) -> str:
        folder = value.strip().lower()
        if folder not in ALLOWED_FOLDERS:
            raise serializers.ValidationError("Invalid folder")
        return folder

    def validate_content_type(self, value: str) -> str:
        ct = value.strip().lower()
        if ct not in ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError("Invalid file type")
        return ct

    def validate_file_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Invalid file name")

        lowered = name.lower()
        if "/" in lowered or "\\" in lowered or ".." in lowered:
            raise serializers.ValidationError("Invalid file name")

        if "." not in lowered:
            raise serializers.ValidationError("File name must have an extension")

        ext = lowered.rsplit(".", 1)[-1]
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            raise serializers.ValidationError("Invalid file extension")

        return name

