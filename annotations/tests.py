import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.request import Request
from annotations.serializers import (
    TagSerializer,
    NoteSerializer,
    build_comment_tree,
)
from annotations.models import Comment, Note
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


class CommentModelTest(TestCase):
    """Unit tests for the Comment model."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='cmnt_testuser',
            email='cmnt@example.com',
            password='pass',
        )
        self.note = Note.objects.create(
            user=self.user,
            note_text='Test note for comments',
        )

    def test_id_has_cmnt_prefix(self):
        """Comment PK must start with 'CMNT_'."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Hello world',
        )
        self.assertTrue(
            comment.id.startswith('CMNT_'),
            f"Expected CMNT_ prefix, got: {comment.id}",
        )

    def test_id_max_length(self):
        """Comment PK must be at most 18 characters."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Length check',
        )
        self.assertLessEqual(len(comment.id), 18)

    def test_top_level_comment_has_no_parent(self):
        """Top-level comment parent_comment must be None."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Root comment',
        )
        self.assertIsNone(comment.parent_comment)

    def test_reply_links_to_parent(self):
        """A reply must reference the correct parent comment."""
        root = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Root',
        )
        reply = Comment.objects.create(
            user=self.user,
            note=self.note,
            parent_comment=root,
            content='Reply',
        )
        self.assertEqual(reply.parent_comment_id, root.id)
        self.assertIn(reply, root.replies.all())

    def test_is_deleted_defaults_to_false(self):
        """is_deleted must default to False on creation."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Default deletion state',
        )
        self.assertFalse(comment.is_deleted)

    def test_soft_delete(self):
        """Soft-deleting sets is_deleted and clears content."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Will be deleted',
        )
        comment.is_deleted = True
        comment.content = ''
        comment.save(update_fields=['is_deleted', 'content'])
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
        self.assertEqual(comment.content, '')

    def test_str_representation(self):
        """__str__ must include truncated content."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Short content',
        )
        self.assertIn('Short content', str(comment))


class CommentTreeTest(TestCase):
    """Tests for the build_comment_tree helper."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='tree_testuser',
            email='tree@example.com',
            password='pass',
        )
        self.note = Note.objects.create(
            user=self.user,
            note_text='Note for tree tests',
        )

    def _make(self, content, parent=None):
        return Comment.objects.create(
            user=self.user,
            note=self.note,
            parent_comment=parent,
            content=content,
        )

    def test_empty_queryset_returns_empty_list(self):
        """build_comment_tree on empty queryset returns []."""
        qs = Comment.objects.filter(note=self.note)
        self.assertEqual(build_comment_tree(qs), [])

    def test_single_root_comment(self):
        """A single root comment yields a list with one node."""
        self._make('Root only')
        qs = (
            Comment.objects
            .filter(note=self.note)
            .select_related('user')
            .order_by('timestamp')
        )
        tree = build_comment_tree(qs)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]['replies'], [])

    def test_nested_replies_appear_under_parent(self):
        """Replies must be nested under their parent node."""
        root = self._make('Root')
        child = self._make('Child', parent=root)
        self._make('Grandchild', parent=child)

        qs = (
            Comment.objects
            .filter(note=self.note)
            .select_related('user')
            .order_by('timestamp')
        )
        tree = build_comment_tree(qs)

        self.assertEqual(len(tree), 1)
        root_node = tree[0]
        self.assertEqual(root_node['content'], 'Root')
        self.assertEqual(len(root_node['replies']), 1)

        child_node = root_node['replies'][0]
        self.assertEqual(child_node['content'], 'Child')
        self.assertEqual(len(child_node['replies']), 1)

        grand_node = child_node['replies'][0]
        self.assertEqual(grand_node['content'], 'Grandchild')
        self.assertEqual(grand_node['replies'], [])

    def test_deleted_comment_content_redacted(self):
        """Soft-deleted comment shows '[deleted]' in tree."""
        root = self._make('Root')
        deleted = Comment.objects.create(
            user=self.user,
            note=self.note,
            parent_comment=root,
            content='',
            is_deleted=True,
        )
        self._make('Reply to deleted', parent=deleted)

        qs = (
            Comment.objects
            .filter(note=self.note)
            .select_related('user')
            .order_by('timestamp')
        )
        tree = build_comment_tree(qs)
        deleted_node = tree[0]['replies'][0]
        self.assertEqual(deleted_node['content'], '[deleted]')
        self.assertEqual(len(deleted_node['replies']), 1)

    def test_multiple_root_comments(self):
        """Multiple root comments all appear at top level."""
        for i in range(3):
            self._make(f'Root {i}')
        qs = (
            Comment.objects
            .filter(note=self.note)
            .select_related('user')
            .order_by('timestamp')
        )
        tree = build_comment_tree(qs)
        self.assertEqual(len(tree), 3)


class CommentViewSetTest(TestCase):
    """Integration tests for the CommentViewSet API."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='api_cmnt_user',
            email='api@example.com',
            password='pass',
        )
        self.other_user = User.objects.create_user(
            username='other_cmnt_user',
            email='other@example.com',
            password='pass',
        )
        self.note = Note.objects.create(
            user=self.user,
            note_text='Note for API tests',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.base_url = (
            f'/api/v1/notes/{self.note.id}/comments/'
        )

    def test_create_top_level_comment(self):
        """POST creates a comment scoped to the note."""
        resp = self.client.post(
            self.base_url,
            {'content': 'Top-level comment'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data['id'].startswith('CMNT_'))
        self.assertEqual(
            data['note_id'], self.note.id
        )
        self.assertIsNone(data['parent_comment'])

    def test_create_reply(self):
        """POST with parent_comment creates a nested reply."""
        root = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Root',
        )
        resp = self.client.post(
            self.base_url,
            {
                'content': 'Reply',
                'parent_comment': root.id,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.json()['parent_comment'], root.id
        )

    def test_list_returns_tree(self):
        """GET list returns nested tree, not a flat list."""
        root = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Root',
        )
        Comment.objects.create(
            user=self.user,
            note=self.note,
            parent_comment=root,
            content='Child',
        )
        resp = self.client.get(self.base_url)
        self.assertEqual(resp.status_code, 200)
        tree = resp.json()
        self.assertEqual(len(tree), 1)
        self.assertEqual(len(tree[0]['replies']), 1)

    def test_soft_delete_preserves_replies(self):
        """DELETE soft-deletes and preserves child replies."""
        root = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Root to delete',
        )
        Comment.objects.create(
            user=self.user,
            note=self.note,
            parent_comment=root,
            content='Child reply',
        )
        resp = self.client.delete(
            f'{self.base_url}{root.id}/'
        )
        self.assertEqual(resp.status_code, 204)
        root.refresh_from_db()
        self.assertTrue(root.is_deleted)
        self.assertTrue(
            Comment.objects.filter(
                parent_comment=root
            ).exists()
        )

    def test_non_owner_cannot_delete(self):
        """DELETE by a different user returns 403."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Owned comment',
        )
        self.client.force_authenticate(
            user=self.other_user
        )
        resp = self.client.delete(
            f'{self.base_url}{comment.id}/'
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_owner_cannot_update(self):
        """PATCH by a different user returns 403."""
        comment = Comment.objects.create(
            user=self.user,
            note=self.note,
            content='Owned comment',
        )
        self.client.force_authenticate(
            user=self.other_user
        )
        resp = self.client.patch(
            f'{self.base_url}{comment.id}/',
            {'content': 'Hijacked'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_parent_comment_cross_note_rejected(self):
        """parent_comment from a different note is rejected."""
        other_note = Note.objects.create(
            user=self.user,
            note_text='Other note',
        )
        foreign_comment = Comment.objects.create(
            user=self.user,
            note=other_note,
            content='Foreign root',
        )
        resp = self.client.post(
            self.base_url,
            {
                'content': 'Invalid reply',
                'parent_comment': foreign_comment.id,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
