import logging

from rest_framework import viewsets
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
            public = True
            logger.debug(
                "Setting public=True due to note_pk "
                "or tag_id filter"
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
