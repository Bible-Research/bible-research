from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from bible.services.sword.client import get_default_sword_client

User = get_user_model()


class SwordClientTests(TestCase):
    def test_sword_client_loads_glucks(self):
        verses = get_default_sword_client().get_chapter_verses(
            'LVSGLU8', 'JHN', 3
        )
        self.assertGreaterEqual(len(verses), 30)
        self.assertEqual(verses[0]['verse_start'], 1)
        self.assertTrue(all(v['verse_text'] for v in verses))

    def test_sword_client_accepts_abbr_gl8(self):
        by_id = get_default_sword_client().get_chapter_verses(
            'LVSGLU8', 'LUK', 20
        )
        by_abbr = get_default_sword_client().get_chapter_verses(
            'GLU8', 'LUK', 20
        )
        self.assertEqual(len(by_abbr), len(by_id))
        self.assertEqual(by_abbr[0]['verse_text'], by_id[0]['verse_text'])


class SwordAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='swordtest',
            email='sword@test.local',
            password='x',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_bible_passage_endpoint_glucks(self):
        url = reverse('bible-passage')
        resp = self.client.get(
            url,
            {'passage': 'John 3', 'fileset_id': 'LVSGLU8'},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['book'], 'JHN')
        self.assertEqual(body['chapter'], 3)
        self.assertEqual(body['format'], 'text')
        self.assertGreaterEqual(len(body['verses']), 30)
        v16 = next(v for v in body['verses'] if v['verse'] == 16)
        self.assertIn('Dievs', v16['text'])

    def test_bible_passage_accepts_abbr_gl8(self):
        url = reverse('bible-passage')
        resp = self.client.get(
            url,
            {'passage': 'Luke 20', 'fileset_id': 'GLU8'},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['book'], 'LUK')
        self.assertEqual(body['chapter'], 20)
        self.assertEqual(body['format'], 'text')
        self.assertGreater(len(body['verses']), 0)

    def test_translations_listing_includes_glucks(self):
        url = reverse('translation-list')
        resp = self.client.get(
            url,
            {'language_iso': 'lvs'},
        )
        self.assertEqual(resp.status_code, 200)
        abbrs = [t['abbr'] for t in resp.json()['results']]
        self.assertIn('GLU8', abbrs)
