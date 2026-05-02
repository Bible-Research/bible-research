"""GCS helpers shared between the audio-generator job (writer) and the
Bible API (reader). Auth via ADC; no JSON keys."""
from __future__ import annotations

import datetime
import json
import logging
import threading
from io import BytesIO
from typing import Optional, Set, Tuple

import google.auth
from google.auth.transport.requests import Request
from google.cloud import storage
from django.conf import settings

logger = logging.getLogger(__name__)

_client: Optional[storage.Client] = None
_client_lock = threading.Lock()


def get_default_client() -> storage.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = storage.Client()
    return _client


def chapter_object_paths(
    fileset_id: str, book_id: str, chapter: int
) -> Tuple[str, str]:
    """Return ``(audio_path, timestamps_path)`` for a chapter."""
    base = f"audio/{fileset_id}/{book_id}/{int(chapter)}"
    return f"{base}_audio.mp3", f"{base}_timestamps.json"


def _bucket():
    return get_default_client().bucket(settings.AUDIO_BUCKET_NAME)


def chapter_audio_exists(
    fileset_id: str, book_id: str, chapter: int
) -> bool:
    audio_path, _ = chapter_object_paths(fileset_id, book_id, chapter)
    return _bucket().blob(audio_path).exists()


def list_completed_chapters(fileset_id: str) -> Set[Tuple[str, int]]:
    """Return the set of ``(book_id, chapter)`` pairs that have **both**
    ``_audio.mp3`` and ``_timestamps.json`` present."""
    prefix = f"audio/{fileset_id}/"
    audio: Set[Tuple[str, int]] = set()
    json_done: Set[Tuple[str, int]] = set()

    for blob in _bucket().list_blobs(prefix=prefix):
        # name = audio/<fileset>/<BOOK>/<CHAPTER>_audio.mp3
        rest = blob.name[len(prefix):]
        try:
            book_id, fname = rest.split("/", 1)
        except ValueError:
            continue
        if fname.endswith("_audio.mp3"):
            try:
                chap = int(fname[: -len("_audio.mp3")])
            except ValueError:
                continue
            audio.add((book_id, chap))
        elif fname.endswith("_timestamps.json"):
            try:
                chap = int(fname[: -len("_timestamps.json")])
            except ValueError:
                continue
            json_done.add((book_id, chap))

    return audio & json_done


def upload_chapter_artifacts(
    fileset_id: str,
    book_id: str,
    chapter: int,
    mp3_bytes: bytes,
    timestamps_payload: dict,
) -> None:
    """Write timestamps JSON first, then MP3, so an MP3 always implies a
    JSON exists (resume logic depends on this)."""
    audio_path, json_path = chapter_object_paths(fileset_id, book_id, chapter)
    bucket = _bucket()

    json_blob = bucket.blob(json_path)
    json_blob.upload_from_string(
        json.dumps(timestamps_payload, ensure_ascii=False),
        content_type="application/json",
    )

    audio_blob = bucket.blob(audio_path)
    audio_blob.upload_from_file(
        BytesIO(mp3_bytes), content_type="audio/mpeg"
    )

    logger.info(
        "Uploaded chapter artifacts: gs://%s/%s",
        bucket.name, audio_path,
    )


def read_timestamps_json(
    fileset_id: str, book_id: str, chapter: int
) -> dict:
    _, json_path = chapter_object_paths(fileset_id, book_id, chapter)
    blob = _bucket().blob(json_path)
    return json.loads(blob.download_as_bytes())


def signed_audio_url(
    fileset_id: str,
    book_id: str,
    chapter: int,
    ttl_seconds: Optional[int] = None,
) -> str:
    """Return a V4 signed URL for the chapter's MP3.

    Works without a JSON key on App Engine / Cloud Run by passing the
    runtime SA's email + an OAuth access token; GCS asks IAM to sign."""
    if ttl_seconds is None:
        ttl_seconds = settings.AUDIO_SIGNED_URL_TTL_SECONDS

    audio_path, _ = chapter_object_paths(fileset_id, book_id, chapter)
    blob = _bucket().blob(audio_path)

    credentials, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/devstorage.read_only",
            "https://www.googleapis.com/auth/iam",
        ]
    )
    credentials.refresh(Request())

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(seconds=ttl_seconds),
        method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
