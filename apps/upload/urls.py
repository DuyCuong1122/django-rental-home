from django.urls import path

from apps.upload.views import PresignedUploadView

urlpatterns = [
    path("presigned-url", PresignedUploadView.as_view(), name="upload-presigned-url"),
]

