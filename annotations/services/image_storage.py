"""GCS helpers for image attachments.

Mirrors bible/services/storage/gcs.py conventions.
Auth via ADC; no JSON keys.
"""
from __future__ import annotations

import datetime
import logging
import os
from typing import Tuple

import google.auth
from google.auth.transport.requests import Request
from google.cloud import storage
from django.conf import settings
from rest_framework import status as drf_status
from rest_framework.exceptions import (
    APIException,
    UnsupportedMediaType,
)


class FileTooLarge(APIException):
    status_code = drf_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "File exceeds maximum allowed size."
    default_code = "file_too_large"


logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _originals_bucket() -> storage.Bucket:
    client = storage.Client()
    return client.bucket(settings.IMAGE_BUCKET_ORIGINALS)


def upload_original(
    image_id: str,
    django_uploaded_file,
) -> Tuple[str, int, str]:
    """Upload a Django UploadedFile to GCS originals bucket.

    Returns ``(gs_uri, size_bytes, content_type)``.

    Raises:
        UnsupportedMediaType: content-type not in allowlist.
        FileTooLarge: file exceeds IMAGE_MAX_BYTES.
    """
    content_type = getattr(
        django_uploaded_file, "content_type", ""
    ) or ""
    if content_type not in _ALLOWED_EXTENSIONS:
        raise UnsupportedMediaType(
            content_type,
            detail=(
                f"Unsupported image type '{content_type}'. "
                f"Allowed: "
                f"{', '.join(_ALLOWED_EXTENSIONS)}."
            ),
        )

    max_bytes = settings.IMAGE_MAX_BYTES
    django_uploaded_file.seek(0, os.SEEK_END)
    size_bytes = django_uploaded_file.tell()
    django_uploaded_file.seek(0)

    if size_bytes > max_bytes:
        raise FileTooLarge(
            f"File too large ({size_bytes} bytes). "
            f"Maximum allowed: {max_bytes} bytes."
        )

    ext = _ALLOWED_EXTENSIONS[content_type]
    object_name = f"originals/{image_id}/source{ext}"

    bucket = _originals_bucket()
    blob = bucket.blob(object_name)
    blob.upload_from_file(
        django_uploaded_file,
        content_type=content_type,
    )

    gs_uri = f"gs://{bucket.name}/{object_name}"
    logger.info(
        "Uploaded image original: %s (%d bytes)",
        gs_uri,
        size_bytes,
    )
    return gs_uri, size_bytes, content_type


def signed_image_url(
    image_id: str,
    storage_url: str,
    ttl_seconds: int | None = None,
) -> str:
    """Return a V4 signed GET URL for an image original.

    Derives the object path from *storage_url*
    (``gs://<bucket>/<object>``).
    """
    if ttl_seconds is None:
        ttl_seconds = settings.IMAGE_SIGNED_URL_TTL_SECONDS

    try:
        without_scheme = storage_url[len("gs://"):]
        bucket_name, object_name = without_scheme.split("/", 1)
    except (ValueError, IndexError):
        logger.error(
            "Cannot parse storage_url for image %s: %r",
            image_id,
            storage_url,
        )
        return storage_url

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)

    credentials, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/devstorage"
            ".read_only",
            "https://www.googleapis.com/auth/iam",
        ]
    )
    credentials.refresh(Request())

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(seconds=ttl_seconds),
        method="GET",
        service_account_email=(
            credentials.service_account_email
        ),
        access_token=credentials.token,
    )
    return url


def delete_original(image_id: str, storage_url: str) -> None:
    """Best-effort delete of the GCS object; 404 is tolerated."""
    try:
        without_scheme = storage_url[len("gs://"):]
        bucket_name, object_name = without_scheme.split("/", 1)
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(object_name)
        blob.delete()
        logger.info(
            "Deleted image original for %s: %s",
            image_id,
            storage_url,
        )
    except Exception:
        logger.exception(
            "Failed to delete GCS object for image %s "
            "(storage_url=%r) — tolerated.",
            image_id,
            storage_url,
        )
