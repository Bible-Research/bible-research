"""Tests for the ESV API provider (Commits 1 & 2)."""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from bible.services.esv.client import (
    ESVClient,
    ESV_AUDIO_BASE_URL,
    _parse_passage,
)
from bible.services.esv.registry import (
    get_esv_translation_listing,
    is_esv_fileset,
)
from bible.serializers import BiblePassageSerializer

User = get_user_model()

_SIMPLE_PASSAGE = (
    "[1] In the beginning God created the heavens and the "
    "earth.\n\n[2] The earth was without form and void, and "
    "darkness was over the face of the deep."
)

_HEADED_PASSAGE = (
    "The Sermon on the Mount\n\n"
    "[1] Seeing the crowds, he went up on the mountain.\n\n"
    "The Beatitudes\n\n"
    "[3] Blessed are the poor in spirit.\n"
    "[4] Blessed are those who mourn."
)


# ============================================================
# Commit 1 — registry helpers
# ============================================================

class ESVRegistryTests(TestCase):
    def test_is_esv_fileset_true(self):
        self.assertTrue(is_esv_fileset("ENGESV_API"))

    def test_is_esv_fileset_case_insensitive(self):
        self.assertTrue(is_esv_fileset("engesv_api"))

    def test_is_esv_fileset_false_for_unknown(self):
        self.assertFalse(is_esv_fileset("ENGESV"))
        self.assertFalse(is_esv_fileset("LVSGLU8"))

    def test_translation_listing_shape(self):
        listing = get_esv_translation_listing()
        self.assertEqual(len(listing), 1)
        entry = listing[0]
        self.assertEqual(entry["abbr"], "ESV")
        self.assertEqual(entry["iso"], "eng")
        filesets = entry["filesets"]
        self.assertEqual(len(filesets), 2)
        types = {f["type"] for f in filesets}
        self.assertIn("text_plain", types)
        self.assertIn("audio", types)
        for f in filesets:
            self.assertEqual(f["id"], "ENGESV_API")
            self.assertEqual(f["size"], "C")


# ============================================================
# Commit 1 — parser (verse extraction)
# ============================================================

class ParsePassageVersesTests(TestCase):
    def test_parse_extracts_two_verses(self):
        result = _parse_passage(_SIMPLE_PASSAGE)
        verses = result["verses"]
        self.assertEqual(len(verses), 2)
        self.assertEqual(verses[0]["verse_start"], 1)
        self.assertIn("In the beginning", verses[0]["verse_text"])
        self.assertEqual(verses[1]["verse_start"], 2)
        self.assertIn("without form", verses[1]["verse_text"])

    def test_parse_returns_empty_headings_when_none(self):
        result = _parse_passage(_SIMPLE_PASSAGE)
        self.assertEqual(result["headings"], [])


# ============================================================
# Commit 1 — client session + URL
# ============================================================

class ESVClientSessionTests(TestCase):
    @override_settings(ESV_KEY="test-key")
    def test_get_chapter_verses_uses_session(self):
        client = ESVClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "passages": [_SIMPLE_PASSAGE]
        }
        mock_resp.raise_for_status = MagicMock()
        client.session.get = MagicMock(return_value=mock_resp)

        verses = client.get_chapter_verses("GEN", 1)

        client.session.get.assert_called_once()
        call_args, call_kwargs = client.session.get.call_args
        self.assertIn(
            "api.esv.org", call_args[0]
        )
        params = call_kwargs.get("params", {})
        self.assertIn("Genesis 1", params.get("q", ""))
        self.assertEqual(len(verses), 2)

    @override_settings(ESV_KEY="test-key")
    def test_authorization_header_is_set(self):
        client = ESVClient(api_key="test-key")
        self.assertIn(
            "Authorization", client.session.headers
        )
        self.assertEqual(
            client.session.headers["Authorization"],
            "Token test-key",
        )

    @override_settings(ESV_KEY=None)
    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            ESVClient(api_key=None)


# ============================================================
# Commit 1 — serializer routing
# ============================================================

class ESVSerializerRoutingTests(TestCase):
    @override_settings(ESV_KEY="test-key")
    @patch(
        "bible.serializers.get_default_esv_client"
    )
    def test_serializer_routes_esv_fileset(self, mock_get):
        mock_client = MagicMock()
        mock_client.get_chapter_with_headings.return_value = {
            "verses": [
                {"verse_start": 1, "verse_text": "ESV text."}
            ],
            "headings": [],
        }
        mock_get.return_value = mock_client

        data = {
            "book": "GEN",
            "book_name": "Genesis",
            "chapter": 1,
            "fileset_id": "ENGESV_API",
            "response_format": "text",
        }
        result = BiblePassageSerializer(data).to_representation(
            data
        )

        self.assertEqual(result["format"], "text")
        self.assertEqual(len(result["verses"]), 1)
        self.assertEqual(
            result["verses"][0]["text"], "ESV text."
        )
        mock_client.get_chapter_with_headings.assert_called_once_with(
            "GEN", 1
        )

    @override_settings(ESV_KEY="test-key")
    @patch(
        "bible.serializers.get_default_esv_client"
    )
    def test_serializer_returns_esv_audio_url(
        self, mock_get
    ):
        mock_client = MagicMock()
        mock_client.get_chapter_audio_url.return_value = (
            "https://cdn.esv.org/audio/genesis_1.mp3"
        )
        mock_get.return_value = mock_client

        data = {
            "book": "GEN",
            "book_name": "Genesis",
            "chapter": 1,
            "fileset_id": "ENGESV_API",
            "response_format": "audio",
        }
        result = BiblePassageSerializer(data).to_representation(
            data
        )
        self.assertEqual(result["format"], "audio")
        self.assertEqual(
            result["audio_url"],
            "https://cdn.esv.org/audio/genesis_1.mp3",
        )
        mock_client.get_chapter_audio_url.assert_called_once_with(
            "GEN", 1
        )


# ============================================================
# get_chapter_audio_url — redirect handling
# ============================================================

class ESVClientAudioTests(TestCase):
    @override_settings(ESV_KEY="test-key")
    def test_returns_location_from_redirect(self):
        client = ESVClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {
            "Location": "https://cdn.esv.org/audio/jhn_3.mp3"
        }
        client.session.get = MagicMock(
            return_value=mock_resp
        )

        url = client.get_chapter_audio_url("JHN", 3)

        self.assertEqual(
            url, "https://cdn.esv.org/audio/jhn_3.mp3"
        )
        call_args, call_kwargs = client.session.get.call_args
        self.assertIn(ESV_AUDIO_BASE_URL, call_args)
        params = call_kwargs.get("params", {})
        self.assertIn("John 3", params.get("q", ""))
        self.assertFalse(
            call_kwargs.get("allow_redirects", True)
        )

    @override_settings(ESV_KEY="test-key")
    def test_raises_if_no_location_header(self):
        client = ESVClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {}
        client.session.get = MagicMock(
            return_value=mock_resp
        )

        with self.assertRaises(ValueError):
            client.get_chapter_audio_url("GEN", 1)

    @override_settings(ESV_KEY="test-key")
    def test_raises_on_non_redirect_status(self):
        client = ESVClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        client.session.get = MagicMock(
            return_value=mock_resp
        )

        with self.assertRaises(ValueError):
            client.get_chapter_audio_url("GEN", 1)


# ============================================================
# Commit 1 — translations endpoint includes ESV
# ============================================================

class ESVTranslationsEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="esvtest",
            email="esv@test.local",
            password="x",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch(
        "bible.services.translation_service."
        "get_default_dbt_client"
    )
    def test_translations_endpoint_includes_esv(
        self, mock_dbt
    ):
        mock_dbt.return_value.get_bibles.return_value = {
            "data": []
        }
        from django.urls import reverse
        url = reverse("translation-list")
        resp = self.client.get(
            url, {"language_iso": "eng"}
        )
        self.assertEqual(resp.status_code, 200)
        abbrs = [t["abbr"] for t in resp.json()["results"]]
        self.assertIn("ESV", abbrs)
        esv_entry = next(
            t for t in resp.json()["results"]
            if t["abbr"] == "ESV"
        )
        fileset_ids = [
            f["id"] for f in esv_entry["filesets"]
        ]
        self.assertIn("ENGESV_API", fileset_ids)


# ============================================================
# Commit 2 — structured headings parse
# ============================================================

class ParsePassageHeadingsTests(TestCase):
    def test_parse_extracts_headings_at_chapter_start(self):
        passage = (
            "The Sermon on the Mount\n\n"
            "[1] Seeing the crowds, he went up."
        )
        result = _parse_passage(passage)
        self.assertEqual(len(result["headings"]), 1)
        self.assertEqual(
            result["headings"][0]["before_verse"], 1
        )
        self.assertEqual(
            result["headings"][0]["text"],
            "The Sermon on the Mount",
        )

    def test_parse_extracts_mid_chapter_heading(self):
        result = _parse_passage(_HEADED_PASSAGE)
        headings = result["headings"]
        texts = [h["text"] for h in headings]
        self.assertIn("The Sermon on the Mount", texts)
        self.assertIn("The Beatitudes", texts)
        beatitudes = next(
            h for h in headings
            if h["text"] == "The Beatitudes"
        )
        self.assertEqual(beatitudes["before_verse"], 3)

    def test_parse_returns_empty_headings_when_none(self):
        result = _parse_passage(_SIMPLE_PASSAGE)
        self.assertEqual(result["headings"], [])

    def test_parse_verses_present_with_headings(self):
        result = _parse_passage(_HEADED_PASSAGE)
        verse_nums = [
            v["verse_start"] for v in result["verses"]
        ]
        self.assertIn(1, verse_nums)
        self.assertIn(3, verse_nums)
        self.assertIn(4, verse_nums)


# ============================================================
# Commit 2 — serializer returns headings for ESV
# ============================================================

class ESVSerializerHeadingsTests(TestCase):
    @override_settings(ESV_KEY="test-key")
    @patch(
        "bible.serializers.get_default_esv_client"
    )
    def test_serializer_returns_headings_for_esv(
        self, mock_get
    ):
        mock_client = MagicMock()
        mock_client.get_chapter_with_headings.return_value = {
            "verses": [
                {"verse_start": 3, "verse_text": "Blessed..."}
            ],
            "headings": [
                {
                    "before_verse": 3,
                    "text": "The Beatitudes",
                }
            ],
        }
        mock_get.return_value = mock_client

        data = {
            "book": "MAT",
            "book_name": "Matthew",
            "chapter": 5,
            "fileset_id": "ENGESV_API",
            "response_format": "text",
        }
        result = BiblePassageSerializer(data).to_representation(
            data
        )
        self.assertIn("headings", result)
        self.assertEqual(len(result["headings"]), 1)
        self.assertEqual(
            result["headings"][0]["text"], "The Beatitudes"
        )
        self.assertEqual(
            result["headings"][0]["before_verse"], 3
        )
