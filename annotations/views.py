import logging

from rest_framework import permissions, viewsets
from django.contrib.auth import get_user_model
from django.db import models

from .models import Tag, Note
from .serializers import (
    TagSerializer,
    NoteSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be created, viewed, updated, or deleted.

    - `retrieve` is public for any tag that has at least one public note,
      so share pages can resolve tag names.
    - `list` and all write actions are restricted to the owning user.
    """
    serializer_class = TagSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

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

    Permissions:
    - `list` and `retrieve` are public (filtered to public-only for anonymous).
    - All write actions require authentication.
    """
    serializer_class = NoteSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

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

        if (user.is_authenticated and
                instance.user != user):
            from rest_framework.exceptions import PermissionDenied
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
            from rest_framework.exceptions import PermissionDenied
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
        Returns the queryset of notes the current caller may see.

        Rules:
        - Anonymous callers see notes where `public=True`, restricted by
          `tag_id`/`pk` if given.
        - Authenticated callers always see their own notes; when the
          request is a share view (by `tag_id` or `pk`) or opts into
          `?public=true`, they also see every other `public=True` note
          matching the filter.
        - Plain `GET /api/v1/notes/` only returns the caller's own notes
          (empty for anonymous).
        """
        user = self.request.user
        note_pk = self.kwargs.get('pk', None)
        tag_id = self.request.query_params.get('tag_id', None)
        public_param = self.request.query_params.get(
            'public', ''
        ).lower() == 'true'
        is_share_view = bool(note_pk or tag_id)

        logger.info(
            "NoteViewSet.get_queryset | user=%s | note_pk=%s | tag_id=%s"
            " | public_param=%s | is_share_view=%s",
            user.username if user.is_authenticated else 'Anonymous',
            note_pk, tag_id, public_param, is_share_view,
        )

        if user.is_authenticated:
            own = models.Q(user=user)
            if is_share_view or public_param:
                queryset = Note.objects.filter(own | models.Q(public=True))
            else:
                queryset = Note.objects.filter(own)
        else:
            queryset = Note.objects.filter(public=True)

        if tag_id:
            queryset = queryset.filter(tag_id=tag_id)
        if note_pk:
            queryset = queryset.filter(id=note_pk)

        final_queryset = queryset.order_by('-created_at')
        logger.info(
            "NoteViewSet.get_queryset returning %d notes",
            final_queryset.count(),
        )
        return final_queryset
