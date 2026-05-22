"""Tests for image attachment endpoints.

GCS is mocked via unittest.mock.patch so no real bucket
credentials are needed.
"""
import io
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from annotations.models import Comment, Image, Note
from annotations.services.image_storage import (
    FileTooLarge,
    upload_original,
)

User = get_user_model()

_SMALL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_file(
    content=_SMALL_PNG,
    name="photo.png",
    content_type="image/png",
):
    """Build an in-memory file object suitable for DRF upload."""
    f = io.BytesIO(content)
    f.name = name
    f.content_type = content_type
    f.size = len(content)
    return f


def _mock_bucket(gs_uri="gs://test-bucket/originals/x/source.png"):
    """Return a context-manager patch for _originals_bucket."""
    bucket = MagicMock()
    bucket.name = "test-bucket"
    blob = MagicMock()
    bucket.blob.return_value = blob
    return patch(
        "annotations.services.image_storage._originals_bucket",
        return_value=bucket,
    )


class ImageModelTest(TestCase):
    """Unit tests for the Image model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="img_model_user",
            email="img_model@example.com",
            password="pass",
        )
        self.note = Note.objects.create(
            user=self.user,
            note_text="Note for image tests",
        )
        self.comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content="Comment for image tests",
        )

    def test_id_has_img_prefix(self):
        """Image PK must start with 'IMG_'."""
        image = Image.objects.create(
            note=self.note,
            uploaded_by=self.user,
            storage_url="gs://b/originals/x/source.png",
        )
        self.assertTrue(
            image.id.startswith("IMG_"),
            f"Expected IMG_ prefix, got: {image.id}",
        )

    def test_id_max_length(self):
        """Image PK must be at most 18 characters."""
        image = Image.objects.create(
            note=self.note,
            uploaded_by=self.user,
            storage_url="gs://b/originals/x/source.png",
        )
        self.assertLessEqual(len(image.id), 18)

    def test_str_includes_parent_note(self):
        image = Image.objects.create(
            note=self.note,
            uploaded_by=self.user,
            storage_url="gs://b/originals/x/source.png",
        )
        self.assertIn("note", str(image))

    def test_str_includes_parent_comment(self):
        image = Image.objects.create(
            comment=self.comment,
            uploaded_by=self.user,
            storage_url=(
                "gs://b/originals/x/source.png"
            ),
        )
        self.assertIn("comment", str(image))

    def test_xor_constraint_rejects_both_parents(self):
        """CheckConstraint must reject an Image with both
        a note and a comment set."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Image.objects.create(
                    note=self.note,
                    comment=self.comment,
                    uploaded_by=self.user,
                    storage_url=(
                        "gs://b/originals/x/source.png"
                    ),
                )

    def test_xor_constraint_rejects_no_parents(self):
        """CheckConstraint must reject an Image with neither
        a note nor a comment set."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Image.objects.create(
                    uploaded_by=self.user,
                    storage_url=(
                        "gs://b/originals/x/source.png"
                    ),
                )


class UploadOriginalServiceTest(TestCase):
    """Unit tests for the upload_original service function."""

    def setUp(self):
        self._override = override_settings(
            IMAGE_MAX_BYTES=10 * 1024 * 1024,
            IMAGE_BUCKET_ORIGINALS="test-bucket",
        )
        self._override.enable()

    def tearDown(self):
        self._override.disable()

    def test_happy_path_returns_tuple(self):
        with _mock_bucket():
            gs_uri, size, ct = upload_original(
                "IMG_TESTID0000001",
                _make_file(),
            )
        self.assertTrue(gs_uri.startswith("gs://"))
        self.assertGreater(size, 0)
        self.assertEqual(ct, "image/png")

    def test_disallowed_content_type_raises_415(self):
        from rest_framework.exceptions import (
            UnsupportedMediaType,
        )
        bad_file = _make_file(
            content=b"fake",
            name="virus.exe",
            content_type="application/octet-stream",
        )
        with _mock_bucket():
            with self.assertRaises(UnsupportedMediaType):
                upload_original("IMG_X", bad_file)

    def test_oversized_file_raises_413(self):
        big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
        big.name = "big.png"
        big.content_type = "image/png"
        with _mock_bucket():
            with self.assertRaises(FileTooLarge):
                upload_original("IMG_X", big)

    def test_object_path_follows_convention(self):
        """GCS object path must be originals/<id>/source<ext>."""
        captured = {}

        def fake_bucket():
            bucket = MagicMock()
            bucket.name = "test-bucket"

            def capture_blob(name):
                captured["name"] = name
                blob = MagicMock()
                return blob

            bucket.blob.side_effect = capture_blob
            return bucket

        with patch(
            "annotations.services.image_storage"
            "._originals_bucket",
            side_effect=fake_bucket,
        ):
            upload_original(
                "IMG_PATHCHECK00001",
                _make_file(),
            )

        self.assertEqual(
            captured.get("name"),
            "originals/IMG_PATHCHECK00001/source.png",
        )

    def test_spoofed_content_type_raises_415(self):
        """Non-image bytes with image/ content-type must fail."""
        from rest_framework.exceptions import (
            UnsupportedMediaType,
        )
        evil = _make_file(
            content=b"not a real image at all",
            name="evil.png",
            content_type="image/png",
        )
        with _mock_bucket():
            with self.assertRaises(UnsupportedMediaType):
                upload_original("IMG_X", evil)


class NoteImageAPITest(TestCase):
    """Integration tests for NoteImageViewSet."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="note_img_owner",
            email="note_img_owner@example.com",
            password="pass",
        )
        self.other = User.objects.create_user(
            username="note_img_other",
            email="note_img_other@example.com",
            password="pass",
        )
        self.note = Note.objects.create(
            user=self.owner,
            note_text="Note for image API tests",
        )
        self.client = APIClient()

    def _upload_url(self):
        return (
            f"/api/v1/notes/{self.note.id}/images/"
        )

    def test_happy_path_upload_to_note(self):
        self.client.force_authenticate(user=self.owner)
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": _make_file()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIn("id", resp.data)
        self.assertTrue(
            resp.data["id"].startswith("IMG_")
        )
        self.assertEqual(Image.objects.count(), 1)

    def test_non_owner_upload_returns_403(self):
        self.client.force_authenticate(user=self.other)
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": _make_file()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Image.objects.count(), 0)

    def test_disallowed_content_type_returns_415(self):
        self.client.force_authenticate(user=self.owner)
        bad_file = _make_file(
            content=b"fake",
            name="doc.pdf",
            content_type="application/pdf",
        )
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": bad_file},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(Image.objects.count(), 0)

    def test_oversized_file_returns_413(self):
        self.client.force_authenticate(user=self.owner)
        big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
        big.name = "big.png"
        big.content_type = "image/png"
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": big},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(Image.objects.count(), 0)

    def test_list_returns_images_for_accessible_note(self):
        Image.objects.create(
            note=self.note,
            uploaded_by=self.owner,
            storage_url="gs://b/originals/x/source.png",
        )
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get(self._upload_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_list_other_user_private_note_returns_403(self):
        self.client.force_authenticate(user=self.other)
        resp = self.client.get(self._upload_url())
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_list_private_note_returns_403(self):
        resp = self.client.get(self._upload_url())
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_list_public_note_returns_200(self):
        """Anon may read images on public notes (plan scope)."""
        self.note.public = True
        self.note.save(update_fields=['public'])
        Image.objects.create(
            note=self.note,
            uploaded_by=self.owner,
            storage_url="gs://b/originals/x/source.png",
        )
        resp = self.client.get(self._upload_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_unauthenticated_upload_returns_403(self):
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": _make_file()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 403)

    def test_upload_without_file_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        resp = self.client.post(
            self._upload_url(),
            {},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_spoofed_content_type_returns_415(self):
        self.client.force_authenticate(user=self.owner)
        evil = _make_file(
            content=b"not a real image at all",
            name="evil.png",
            content_type="image/png",
        )
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": evil},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(Image.objects.count(), 0)


class CommentImageAPITest(TestCase):
    """Integration tests for CommentImageViewSet."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="cmnt_img_owner",
            email="cmnt_img_owner@example.com",
            password="pass",
        )
        self.other = User.objects.create_user(
            username="cmnt_img_other",
            email="cmnt_img_other@example.com",
            password="pass",
        )
        self.note = Note.objects.create(
            user=self.owner,
            note_text="Note for comment image tests",
        )
        self.comment = Comment.objects.create(
            user=self.owner,
            note=self.note,
            content="Comment for image tests",
        )
        self.client = APIClient()

    def _upload_url(self):
        return (
            f"/api/v1/notes/{self.note.id}"
            f"/comments/{self.comment.id}/images/"
        )

    def test_happy_path_upload_to_comment(self):
        self.client.force_authenticate(user=self.owner)
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": _make_file()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(
            resp.data["id"].startswith("IMG_")
        )
        img = Image.objects.get(pk=resp.data["id"])
        self.assertEqual(img.comment_id, self.comment.id)

    def test_non_author_upload_returns_403(self):
        self.client.force_authenticate(user=self.other)
        with _mock_bucket():
            resp = self.client.post(
                self._upload_url(),
                {"file": _make_file()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 403)


class ImageDeleteAPITest(TestCase):
    """Integration tests for ImageDestroyView."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="img_del_owner",
            email="img_del_owner@example.com",
            password="pass",
        )
        self.other = User.objects.create_user(
            username="img_del_other",
            email="img_del_other@example.com",
            password="pass",
        )
        self.note = Note.objects.create(
            user=self.owner,
            note_text="Note for delete tests",
        )
        self.image = Image.objects.create(
            note=self.note,
            uploaded_by=self.owner,
            storage_url=(
                "gs://test-bucket/originals"
                "/IMG_DELTEST00001/source.png"
            ),
        )
        self.client = APIClient()

    def _delete_url(self):
        return f"/api/v1/images/{self.image.id}/"

    def test_unauthenticated_delete_returns_401(self):
        resp = self.client.delete(self._delete_url())
        self.assertEqual(resp.status_code, 401)
        self.assertTrue(
            Image.objects.filter(pk=self.image.id).exists()
        )

    def test_non_owner_delete_returns_403(self):
        self.client.force_authenticate(user=self.other)
        resp = self.client.delete(self._delete_url())
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(
            Image.objects.filter(pk=self.image.id).exists()
        )

    def test_owner_delete_removes_row_and_calls_gcs(self):
        self.client.force_authenticate(user=self.owner)
        mock_blob = MagicMock()
        mock_gcs_client = MagicMock()
        mock_gcs_client.bucket.return_value.blob.return_value = (
            mock_blob
        )
        with patch(
            "annotations.services.image_storage._get_client",
            return_value=mock_gcs_client,
        ):
            resp = self.client.delete(self._delete_url())

        self.assertEqual(resp.status_code, 204)
        self.assertFalse(
            Image.objects.filter(pk=self.image.id).exists()
        )
        mock_blob.delete.assert_called_once()
