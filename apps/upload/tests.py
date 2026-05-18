from __future__ import annotations

from urllib.parse import urlparse
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from apps.upload.services import S3UploadService


class PresignedUploadTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_requires_auth(self) -> None:
        resp = self.client.post(
            "/api/v1/upload/presigned-url",
            data={"folder": "avatars", "file_name": "avatar.jpg", "content_type": "image/jpeg"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    @patch("apps.upload.services.S3UploadService.generate_presigned_upload_url")
    @patch("apps.upload.views.decode_token")
    def test_generate_presigned_url_success(self, decode_token_mock, generate_mock) -> None:
        decode_token_mock.return_value = {"sub": "user-1", "role": "TENANT"}
        generate_mock.return_value = type(
            "R",
            (),
            {
                "upload_url": "https://s3-presigned.example.com",
                "file_url": "https://bucket.s3.region.amazonaws.com/avatars/key.jpg",
                "expires_in": 3600,
            },
        )()

        resp = self.client.post(
            "/api/v1/upload/presigned-url",
            data={"folder": "avatars", "file_name": "avatar.jpg", "content_type": "image/jpeg"},
            format="json",
            HTTP_AUTHORIZATION="Bearer testtoken",
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("data", body)
        self.assertEqual(body["data"]["expires_in"], 3600)
        self.assertTrue(body["data"]["upload_url"])
        self.assertTrue(body["data"]["file_url"])

    @patch("apps.upload.views.decode_token")
    def test_invalid_folder(self, decode_token_mock) -> None:
        decode_token_mock.return_value = {"sub": "user-1", "role": "TENANT"}
        resp = self.client.post(
            "/api/v1/upload/presigned-url",
            data={"folder": "evil", "file_name": "avatar.jpg", "content_type": "image/jpeg"},
            format="json",
            HTTP_AUTHORIZATION="Bearer testtoken",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])

    @patch("apps.upload.views.decode_token")
    def test_invalid_content_type(self, decode_token_mock) -> None:
        decode_token_mock.return_value = {"sub": "user-1", "role": "TENANT"}
        resp = self.client.post(
            "/api/v1/upload/presigned-url",
            data={"folder": "avatars", "file_name": "avatar.jpg", "content_type": "image/gif"},
            format="json",
            HTTP_AUTHORIZATION="Bearer testtoken",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])


class S3UploadServiceTests(SimpleTestCase):
    @override_settings(
        AWS_ACCESS_KEY_ID="ak",
        AWS_SECRET_ACCESS_KEY="sk",
        AWS_BUCKET_NAME="bucket",
        AWS_REGION="ap-southeast-2",
    )
    @patch("apps.upload.services.boto3.client")
    def test_presigned_url_uses_configured_region(self, boto_client_mock) -> None:
        s3_client = boto_client_mock.return_value
        s3_client.generate_presigned_url.return_value = (
            "https://bucket.s3.ap-southeast-2.amazonaws.com/avatars/x.jpg?X-Amz-SignedHeaders=content-type%3Bhost"
        )

        service = S3UploadService()
        result = service.generate_presigned_upload_url(
            folder="avatars",
            file_name="avatar.jpg",
            content_type="image/jpeg",
        )

        boto_client_mock.assert_called_once()
        self.assertEqual(boto_client_mock.call_args.kwargs["region_name"], "ap-southeast-2")
        s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = s3_client.generate_presigned_url.call_args.kwargs
        self.assertNotIn("ACL", call_kwargs["Params"])
        self.assertEqual(urlparse(result.upload_url).netloc, "bucket.s3.ap-southeast-2.amazonaws.com")
        self.assertIn("bucket.s3.ap-southeast-2.amazonaws.com/avatars/", result.file_url)
