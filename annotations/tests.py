import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.request import Request
from annotations.models import Note, Tag
from annotations.serializers import TagSerializer, NoteSerializer
from bible.models import Verse


class SerializerTestCase(TestCase):
    """Test case for Tag and Note serializers with an authenticated user."""

    def setUp(self):
        """Set up test data and authentication."""
        # Create a test user
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password123'
        )

        # Create a factory for requests
        factory = APIRequestFactory()
        request = factory.get('/')
        # Force authentication
        request.user = self.user
        # Create a proper request context
        self.context = {'request': Request(request)}

        # Create test verse
        self.verse, _ = Verse.objects.get_or_create(
            book='John',
            chapter=3,
            verse=16
        )

    def test_tag_serializer(self):
        """Test that TagSerializer correctly creates a tag."""
        # Use timestamp to ensure unique tag name
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        tag_data = {'name': f'AuthTag_{timestamp}'}
        
        # Create and validate serializer
        tag_serializer = TagSerializer(data=tag_data, context=self.context)
        self.assertTrue(tag_serializer.is_valid(), f"Tag validation errors: {tag_serializer.errors}")
        
        # Save and verify tag
        tag = tag_serializer.save()
        self.assertIsNotNone(tag.id)
        self.assertEqual(tag.name, tag_data['name'])
        
        return tag  # Return for use in other tests

    def test_note_serializer(self):
        """Test that NoteSerializer correctly creates a note with verse references."""
        # First create a tag to associate with the note
        tag = self.test_tag_serializer()
        
        # Prepare note data
        note_data = {
            'note_text': 'This is a test note with authenticated user',
            'tag': tag.id,
            'verse_references': [
                {'book': 'John', 'chapter': 3, 'verse': 16}
            ]
        }
        
        # Create and validate serializer
        note_serializer = NoteSerializer(data=note_data, context=self.context)
        self.assertTrue(note_serializer.is_valid(), f"Note validation errors: {note_serializer.errors}")
        
        # Save and verify note
        note = note_serializer.save()
        self.assertIsNotNone(note.id)
        self.assertEqual(note.note_text, note_data['note_text'])
        self.assertEqual(note.tag.id, tag.id)
        
        # Verify verse references
        self.assertEqual(note.verses.count(), 1)
        verse = note.verses.first()
        self.assertEqual(verse.book, 'John')
        self.assertEqual(verse.chapter, 3)
        self.assertEqual(verse.verse, 16)


class PublicNoteSharingTests(TestCase):
    """End-to-end tests for the public note sharing flow.

    Covers Bible-Research/bible-research#9:
    - Anonymous GET of notes by tag_id returns only public notes.
    - Anonymous GET of a public note by id succeeds; private 404s.
    - Authenticated user sees own private notes + others' public notes
      when filtering by tag_id, never others' private notes.
    - Write actions require authentication.
    - is_owner is true only for the note's owner.
    - Tag retrieve is anonymously accessible for tags with public notes.
    """

    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner', password='pw-owner'
        )
        self.other = User.objects.create_user(
            username='other', password='pw-other'
        )

        self.owner_token = Token.objects.create(user=self.owner).key
        self.other_token = Token.objects.create(user=self.other).key

        self.owner_tag = Tag.objects.create(user=self.owner, name='OwnerTag')
        self.other_tag = Tag.objects.create(user=self.other, name='OtherTag')

        self.owner_public = Note.objects.create(
            user=self.owner, tag=self.owner_tag,
            note_text='owner public note', public=True,
        )
        self.owner_private = Note.objects.create(
            user=self.owner, tag=self.owner_tag,
            note_text='owner private note', public=False,
        )
        self.other_public = Note.objects.create(
            user=self.other, tag=self.other_tag,
            note_text='other public note', public=True,
        )
        self.other_private = Note.objects.create(
            user=self.other, tag=self.other_tag,
            note_text='other private note', public=False,
        )

        self.anon = APIClient()
        self.owner_client = APIClient()
        self.owner_client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.owner_token}'
        )
        self.other_client = APIClient()
        self.other_client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.other_token}'
        )

    def _note_ids(self, response):
        return {item['id'] for item in response.data}

    def test_anonymous_list_by_tag_returns_only_public(self):
        url = reverse('note-list')
        resp = self.anon.get(url, {'tag_id': self.other_tag.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._note_ids(resp)
        self.assertIn(self.other_public.id, ids)
        self.assertNotIn(self.other_private.id, ids)
        self.assertNotIn(self.owner_public.id, ids)
        self.assertNotIn(self.owner_private.id, ids)

    def test_anonymous_retrieve_public_note_ok(self):
        url = reverse('note-detail', args=[self.owner_public.id])
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], self.owner_public.id)
        self.assertFalse(resp.data['is_owner'])

    def test_anonymous_retrieve_private_note_404(self):
        url = reverse('note-detail', args=[self.owner_private.id])
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_list_by_others_tag_mixes_own_and_public(self):
        cross_tag_private = Note.objects.create(
            user=self.owner, tag=self.other_tag,
            note_text='cross-tag private', public=False,
        )
        url = reverse('note-list')
        resp = self.owner_client.get(url, {'tag_id': self.other_tag.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._note_ids(resp)
        self.assertIn(self.other_public.id, ids)
        self.assertIn(cross_tag_private.id, ids)
        self.assertNotIn(self.other_private.id, ids)

    def test_authenticated_plain_list_returns_only_own(self):
        url = reverse('note-list')
        resp = self.owner_client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._note_ids(resp)
        self.assertEqual(ids, {self.owner_public.id, self.owner_private.id})

    def test_is_owner_flag(self):
        url = reverse('note-detail', args=[self.owner_public.id])
        owner_resp = self.owner_client.get(url)
        other_resp = self.other_client.get(url)
        self.assertTrue(owner_resp.data['is_owner'])
        self.assertFalse(other_resp.data['is_owner'])

    def test_anonymous_cannot_write(self):
        url = reverse('note-list')
        payload = {
            'note_text': 'nope', 'public': True, 'tag': self.owner_tag.id,
        }
        self.assertEqual(
            self.anon.post(url, payload, format='json').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        detail = reverse('note-detail', args=[self.owner_public.id])
        self.assertEqual(
            self.anon.patch(detail, {'note_text': 'x'}).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.anon.delete(detail).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_tag_retrieve_public_for_tag_with_public_note(self):
        url = reverse('tag-detail', args=[self.other_tag.id])
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'OtherTag')

    def test_tag_retrieve_404_when_no_public_notes(self):
        private_only = Tag.objects.create(
            user=self.owner, name='PrivateOnly'
        )
        Note.objects.create(
            user=self.owner, tag=private_only,
            note_text='private', public=False,
        )
        url = reverse('tag-detail', args=[private_only.id])
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_tag_list_requires_auth(self):
        url = reverse('tag-list')
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
