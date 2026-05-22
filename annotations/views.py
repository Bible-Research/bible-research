import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets, status as drf_status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from .models import Tag, Note, Comment, Image, generate_image_id
from .serializers import (
    TagSerializer,
    NoteSerializer,
    CommentSerializer,
    ImageSerializer,
    build_comment_tree,
)
from .services.image_storage import upload_original, delete_original

User = get_user_model()
logger = logging.getLogger(__name__)


NOTE_IDS_CAP = 200


def get_accessible_notes_qs(user):
    """
    Return a Note queryset scoped to what *user* may see:
    - Authenticated → own notes ∪ public notes
    - Anonymous     → public notes only
    """
    if user.is_authenticated:
        return Note.objects.filter(
            Q(user=user) | Q(public=True)
        )
    return Note.objects.filter(public=True)


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be created, viewed, updated, or deleted.

    Users can only see and manage their own tags.
    """
    serializer_class = TagSerializer

    def get_queryset(self):
        """
        Returns the queryset of tags that the current user
        has access to.
        Authenticated users see their own tags.
        Unauthenticated users see the guest user's tags.
        """
        user = self.request.user
        logger.info(
            f"TagViewSet.get_queryset called for user: "
            f"{user.username if user.is_authenticated else 'Anonymous'}"
        )

        # For authenticated users, return their own tags
        if user.is_authenticated:
            queryset = Tag.objects.filter(
                user=user
            ).order_by('name')
            logger.debug(
                f"Returning {queryset.count()} tags "
                f"for user {user.username}"
            )
            return queryset

        # For unauthenticated users, return guest user's tags
        try:
            guest_user = User.objects.get(username='guest')
            queryset = Tag.objects.filter(
                user=guest_user
            ).order_by('name')
            logger.debug(
                f"Returning {queryset.count()} tags "
                f"for guest user"
            )
            return queryset
        except User.DoesNotExist:
            logger.warning(
                "Guest user does not exist, "
                "returning empty queryset"
            )
            return Tag.objects.none()

    def perform_create(self, serializer):
        """
        Assigns the current authenticated user as the creator
        of the tag when a new tag is created.
        """
        user = self.request.user
        tag_name = serializer.validated_data.get('name', 'N/A')

        if user.is_authenticated:
            logger.info(
                f"Creating tag '{tag_name}' "
                f"for user {user.username}"
            )
            serializer.save(user=user)
        else:
            # For unauthenticated users, use guest user
            try:
                guest_user = User.objects.get(username='guest')
                logger.info(
                    f"Creating tag '{tag_name}' "
                    f"for guest user"
                )
                serializer.save(user=guest_user)
            except User.DoesNotExist:
                logger.error(
                    f"Guest user does not exist, "
                    f"creating tag '{tag_name}' "
                    f"without user assignment"
                )
                serializer.save()

    def perform_update(self, serializer):
        """
        Ensures that a user can only update their own tags.
        """
        instance = serializer.instance
        user = self.request.user
        logger.info(
            f"Updating tag '{instance.name}' (ID: {instance.id}) "
            f"by user: "
            f"{user.username if user.is_authenticated else 'Anonymous'}"
        )
        serializer.save()

    def perform_destroy(self, instance):
        """
        Ensures that a user can only delete their own tags.
        """
        user = self.request.user
        logger.info(
            f"Deleting tag '{instance.name}' (ID: {instance.id}) "
            f"by user: "
            f"{user.username if user.is_authenticated else 'Anonymous'}"
        )
        instance.delete()
        logger.debug(
            f"Tag '{instance.name}' "
            f"successfully deleted"
        )


class NoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows notes to be created, viewed, updated, or deleted.
    Authenticated users see and manage their own notes.
    Unauthenticated users can view notes marked as public.

    Additional filtering:
    - GET /api/v1/notes/?tag_id={tag_id} - List notes filtered by tag ID
    - GET /api/v1/notes/?public=true - List both public and private notes
    """
    serializer_class = NoteSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Assigns the current authenticated user as the creator
        of the note when a new note is created.
        """
        user = self.request.user
        if user.is_authenticated:
            note_text = serializer.validated_data.get(
                'text',
                'N/A'
            )[:50]
            logger.info(
                f"Creating note for user {user.username}: "
                f"{note_text}..."
            )
            serializer.save(user=user)
        else:
            logger.warning(
                "Unauthenticated user attempted "
                "to create a note"
            )

    def perform_update(self, serializer):
        """
        Ensures that a user can only update their own notes.
        Raises PermissionDenied if a user attempts to update
        another user's note.
        """
        instance = serializer.instance
        user = self.request.user

        logger.info(
            f"Attempting to update note ID: {instance.id} "
            f"by user: "
            f"{user.username if user.is_authenticated else 'Anonymous'}"
        )

        if user.is_authenticated and instance.user != user:
            logger.warning(
                f"Permission denied: User {user.username} "
                f"attempted to update note ID: {instance.id} "
                f"owned by {instance.user.username}"
            )
            raise PermissionDenied(
                "You do not have permission "
                "to update this note."
            )
        logger.debug(
            f"Note ID: {instance.id} "
            f"successfully updated"
        )
        serializer.save()

    def perform_destroy(self, instance):
        """
        Ensures that a user can only delete their own notes.
        Raises PermissionDenied if a user attempts to delete
        another user's note.
        """
        user = self.request.user

        logger.info(
            f"Attempting to delete note ID: {instance.id} "
            f"by user: "
            f"{user.username if user.is_authenticated else 'Anonymous'}"
        )

        if (user.is_authenticated and
                instance.user != user):
            logger.warning(
                f"Permission denied: User {user.username} "
                f"attempted to delete note ID: {instance.id} "
                f"owned by {instance.user.username}"
            )
            raise PermissionDenied(
                "You do not have permission "
                "to delete this note."
            )
        logger.debug(
            f"Note ID: {instance.id} "
            f"successfully deleted"
        )
        instance.delete()

    def get_queryset(self):
        """
        Returns the queryset of notes that the current user
        has access to.
        - Authenticated users see their own private notes
          by default
        - Unauthenticated users see only public notes

        Available query parameters:
        - GET /api/v1/notes/ - List user's own notes
        - GET /api/v1/notes/?public=true - List public notes
          and user's notes
        - GET /api/v1/notes/<pk>/ - Retrieve a specific note
          by its ID
        - GET /api/v1/notes/?tag_id=<tag_id> - Filter by
          tag ID

        Special cases:
        - When requesting a specific note by ID:
          Users see the note if it's public or their own
        - When filtering by tag_id:
          Users see all public notes with that tag and
          their own notes
        """
        user = self.request.user
        note_pk = self.kwargs.get('pk', None)
        tag_id = self.request.query_params.get('tag_id', None)

        logger.info(
            f"NoteViewSet.get_queryset called for user: "
            f"{user.username if user.is_authenticated else 'Anonymous'} "
            f"| note_pk: {note_pk} | tag_id: {tag_id}"
        )

        if note_pk or tag_id:
            # If specific note or tag is requested,
            # search it in public notes
            queryset = get_accessible_notes_qs(user)
            logger.debug(
                "Using get_accessible_notes_qs due to "
                "note_pk or tag_id filter"
            )
        else:
            # Otherwise evaluate if user requested public notes
            public_param = self.request.query_params.get(
                'public',
                ''
            ).lower()
            public = public_param == 'true'
            logger.debug(
                f"Public parameter: {public_param}, "
                f"public={public}"
            )

            if user.is_authenticated:
                user_notes = models.Q(user=user)
                if public:
                    queryset = Note.objects.filter(
                        user_notes | models.Q(public=True)
                    )
                    logger.debug(
                        f"Authenticated user {user.username}: "
                        f"Fetching own notes + public notes"
                    )
                else:
                    queryset = Note.objects.filter(user_notes)
                    logger.debug(
                        f"Authenticated user {user.username}: "
                        f"Fetching only own notes"
                    )
            else:
                queryset = Note.objects.filter(public=public)
                logger.debug(
                    "Unauthenticated user: "
                    "Fetching public notes only"
                )

        if tag_id:
            queryset = queryset.filter(tag_id=tag_id)
            logger.debug(f"Filtering by tag_id: {tag_id}")

        if note_pk:
            queryset = queryset.filter(id=note_pk)
            logger.debug(f"Filtering by note_pk: {note_pk}")

        final_queryset = queryset.order_by('-created_at')
        logger.info(
            f"Returning {final_queryset.count()} notes"
        )
        return final_queryset


class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for threaded comments on a Note.

    URL pattern (nested under a note):
      GET    /api/v1/notes/{note_pk}/comments/
          Returns the full comment tree for the note.
          Root-level comments are returned with nested
          'replies' lists. Deleted comments appear as
          '[deleted]' to preserve thread structure.

      POST   /api/v1/notes/{note_pk}/comments/
          Create a top-level or reply comment.
          Pass 'parent_comment' PK to create a reply.

      GET    /api/v1/notes/{note_pk}/comments/{pk}/
          Retrieve a single comment (flat).

      PATCH  /api/v1/notes/{note_pk}/comments/{pk}/
          Update a comment's content.

      DELETE /api/v1/notes/{note_pk}/comments/{pk}/
          Soft-delete: sets is_deleted=True and clears
          content. Thread structure is preserved.

    N+1 prevention:
      get_queryset() issues one DB query with
      select_related('user') for all list and tree
      operations. build_comment_tree() assembles the
      hierarchy entirely in Python.
    """

    serializer_class = CommentSerializer
    http_method_names = [
        'get', 'post', 'patch', 'delete', 'head', 'options',
    ]

    def _get_note(self):
        """Return the parent Note or raise 404."""
        return get_object_or_404(
            Note, pk=self.kwargs['note_pk']
        )

    def get_queryset(self):
        """
        Return all comments for the note in one query.
        select_related('user') prevents per-comment author
        lookups during serialization.
        """
        note_pk = self.kwargs['note_pk']
        return (
            Comment.objects
            .filter(note_id=note_pk)
            .select_related('user')
            .order_by('timestamp')
        )

    def list(self, request, *args, **kwargs):
        """Return comments as a nested tree (no N+1)."""
        queryset = self.get_queryset()
        tree = build_comment_tree(queryset)
        logger.info(
            f"Returning comment tree for note "
            f"{self.kwargs.get('note_pk')} "
            f"({len(queryset)} total comments)"
        )
        return Response(tree)

    def perform_create(self, serializer):
        """Inject request user and parent note on create."""
        note = self._get_note()
        user = self.request.user
        logger.info(
            f"User {user.username} creating comment "
            f"on note {note.id}"
        )
        serializer.save(user=user, note=note)

    def perform_update(self, serializer):
        """Allow only the comment author to update."""
        instance = serializer.instance
        user = self.request.user
        if instance.user != user:
            raise PermissionDenied(
                "You do not have permission "
                "to edit this comment."
            )
        logger.info(
            f"User {user.username} updating "
            f"comment {instance.id}"
        )
        serializer.save()

    def perform_destroy(self, instance):
        """
        Soft-delete: mark as deleted and redact content.
        The row is retained so child replies remain intact.
        """
        user = self.request.user
        if instance.user != user:
            raise PermissionDenied(
                "You do not have permission "
                "to delete this comment."
            )
        logger.info(
            f"User {user.username} soft-deleting "
            f"comment {instance.id}"
        )
        instance.is_deleted = True
        instance.content = ''
        instance.save(update_fields=['is_deleted', 'content'])


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='tag_id',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                'Return counts for every accessible note '
                'carrying this tag. Mutually exclusive '
                'with note_ids.'
            ),
            required=False,
        ),
        OpenApiParameter(
            name='note_ids',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                'Comma-separated note PKs (max 200). '
                'Mutually exclusive with tag_id.'
            ),
            required=False,
        ),
        OpenApiParameter(
            name='include_deleted',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description=(
                'When true, soft-deleted comments are '
                'included in the count. Default false.'
            ),
            required=False,
        ),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'counts': {
                    'type': 'object',
                    'additionalProperties': {'type': 'integer'},
                    'example': {
                        'NOT0123': 5,
                        'NOT0456': 0,
                    },
                },
            },
        }
    },
)
class CommentCountView(APIView):
    """
    GET /api/v1/comments/counts/

    Returns the number of (non-deleted) comments per Note.
    Exactly one of tag_id or note_ids must be supplied.
    """

    def get(self, request):
        params = request.query_params
        tag_id = params.get('tag_id')
        note_ids_raw = params.get('note_ids')
        include_deleted = (
            params.get('include_deleted', 'false').lower()
            == 'true'
        )

        has_tag = bool(tag_id)
        has_ids = bool(note_ids_raw)

        if has_tag and has_ids:
            raise ValidationError(
                'Provide either tag_id or note_ids, not both.'
            )
        if not has_tag and not has_ids:
            raise ValidationError(
                'One of tag_id or note_ids is required.'
            )

        note_ids = []
        if has_ids:
            raw_parts = [
                p.strip() for p in note_ids_raw.split(',')
                if p.strip()
            ]
            if len(raw_parts) > NOTE_IDS_CAP:
                raise ValidationError(
                    f'note_ids may contain at most '
                    f'{NOTE_IDS_CAP} IDs.'
                )
            note_ids = raw_parts

        notes_qs = get_accessible_notes_qs(request.user)

        if has_tag:
            notes_qs = notes_qs.filter(tag_id=tag_id)
        else:
            notes_qs = notes_qs.filter(id__in=note_ids)

        count_filter = (
            Q()
            if include_deleted
            else Q(comments__is_deleted=False)
        )
        rows = (
            notes_qs
            .annotate(
                comment_count=Count(
                    'comments',
                    filter=count_filter,
                ),
            )
            .values_list('id', 'comment_count')
        )

        counts = {note_id: cnt for note_id, cnt in rows}
        logger.info(
            f"CommentCountView returning counts for "
            f"{len(counts)} notes"
        )
        return Response({'counts': counts})


class NoteImageViewSet(viewsets.GenericViewSet):
    """
    Image attachments scoped to a Note.

      GET  /api/v1/notes/{note_pk}/images/
      POST /api/v1/notes/{note_pk}/images/

    Upload: multipart/form-data with a single 'file' field.
    Requester must be the note's owner.
    Read: same accessibility scope as get_accessible_notes_qs.
    """

    serializer_class = ImageSerializer
    parser_classes = [MultiPartParser]

    def _get_note(self):
        return get_object_or_404(
            Note, pk=self.kwargs['note_pk']
        )

    def list(self, request, note_pk=None):
        note = self._get_note()
        accessible = get_accessible_notes_qs(request.user)
        if not accessible.filter(pk=note.pk).exists():
            raise PermissionDenied(
                "You do not have access to this note."
            )
        images = Image.objects.filter(note=note)
        serializer = ImageSerializer(
            images, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def create(self, request, note_pk=None):
        note = self._get_note()
        user = request.user
        if not user.is_authenticated or note.user != user:
            raise PermissionDenied(
                "Only the note's owner may upload images."
            )
        max_images = getattr(
            settings, 'IMAGE_MAX_PER_NOTE', 10
        )
        if Image.objects.filter(
            note=note
        ).count() >= max_images:
            raise ValidationError(
                {'file': (
                    f'Maximum {max_images} images per note.'
                )}
            )
        file_obj = request.FILES.get('file')
        if not file_obj:
            raise ValidationError({'file': 'No file provided.'})

        image_id = generate_image_id()
        gs_uri, size_bytes, content_type = upload_original(
            image_id, file_obj
        )
        try:
            image = Image.objects.create(
                id=image_id,
                note=note,
                uploaded_by=user,
                storage_url=gs_uri,
                size_bytes=size_bytes,
                content_type=content_type,
            )
        except Exception:
            delete_original(image_id, gs_uri)
            raise
        logger.info(
            "User %s uploaded image %s to note %s",
            user.username, image.id, note.id,
        )
        serializer = ImageSerializer(
            image, context={'request': request}
        )
        return Response(serializer.data, status=201)


class CommentImageViewSet(viewsets.GenericViewSet):
    """
    Image attachments scoped to a Comment.

      GET  /api/v1/notes/{note_pk}/comments/{comment_pk}/images/
      POST /api/v1/notes/{note_pk}/comments/{comment_pk}/images/

    Upload: multipart/form-data with a single 'file' field.
    Requester must be the comment's author.
    """

    serializer_class = ImageSerializer
    parser_classes = [MultiPartParser]

    def _get_comment(self):
        return get_object_or_404(
            Comment,
            pk=self.kwargs['comment_pk'],
            note_id=self.kwargs['note_pk'],
        )

    def list(self, request, note_pk=None, comment_pk=None):
        comment = self._get_comment()
        accessible = get_accessible_notes_qs(request.user)
        if not accessible.filter(
            pk=comment.note_id
        ).exists():
            raise PermissionDenied(
                "You do not have access to this comment."
            )
        images = Image.objects.filter(comment=comment)
        serializer = ImageSerializer(
            images, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def create(
        self, request, note_pk=None, comment_pk=None
    ):
        comment = self._get_comment()
        user = request.user
        if not user.is_authenticated or comment.user != user:
            raise PermissionDenied(
                "Only the comment's author may upload images."
            )
        max_images = getattr(
            settings, 'IMAGE_MAX_PER_COMMENT', 5
        )
        if Image.objects.filter(
            comment=comment
        ).count() >= max_images:
            raise ValidationError(
                {'file': (
                    f'Maximum {max_images} images per comment.'
                )}
            )
        file_obj = request.FILES.get('file')
        if not file_obj:
            raise ValidationError({'file': 'No file provided.'})

        image_id = generate_image_id()
        gs_uri, size_bytes, content_type = upload_original(
            image_id, file_obj
        )
        try:
            image = Image.objects.create(
                id=image_id,
                comment=comment,
                uploaded_by=user,
                storage_url=gs_uri,
                size_bytes=size_bytes,
                content_type=content_type,
            )
        except Exception:
            delete_original(image_id, gs_uri)
            raise
        logger.info(
            "User %s uploaded image %s to comment %s",
            user.username, image.id, comment.id,
        )
        serializer = ImageSerializer(
            image, context={'request': request}
        )
        return Response(serializer.data, status=201)


class ImageDestroyView(APIView):
    """
    DELETE /api/v1/images/{image_pk}/

    Only the uploader or the parent owner may delete.
    Hard-delete: DB row removed and GCS object deleted
    (best-effort).
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, image_pk):
        image = get_object_or_404(Image, pk=image_pk)
        user = request.user

        is_uploader = image.uploaded_by == user
        is_note_owner = (
            image.note is not None
            and image.note.user == user
        )
        is_comment_author = (
            image.comment is not None
            and image.comment.user == user
        )

        if not (is_uploader or is_note_owner or is_comment_author):
            raise PermissionDenied(
                "You do not have permission to delete "
                "this image."
            )

        storage_url = image.storage_url
        image_id = image.id
        image.delete()
        delete_original(image_id, storage_url)
        logger.info(
            "User %s deleted image %s",
            user.username, image_id,
        )
        return Response(status=drf_status.HTTP_204_NO_CONTENT)
