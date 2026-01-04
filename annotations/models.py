import uuid
from django.db import models
from django.db.models import UniqueConstraint, Q
from bible.models import Verse
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_tag_id():
    return f"TAG{str(uuid.uuid4()).upper().replace('-', '')[:15]}"


class Tag(models.Model):
    """
    Represents a user-defined tag for organizing content.
    Tags can be hierarchical (e.g., 'Love' as parent of 'Reckless love').
    """

    id = models.CharField(
        max_length=18,
        default=generate_tag_id,
        primary_key=True,
        editable=False,
        help_text="Unique identifier for the tag."
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tags',
        null=True,
        blank=True,
        help_text="The user who created this tag."
    )
    name = models.CharField(
        max_length=100,
        # Users can have tags with the same name, but not for the same user.
        unique=False,
        help_text="The name of the tag (e.g., 'Love', 'Grace')."
    )
    parent_tag = models.ForeignKey(
        # Refers to the Tag model itself, allowing for hierarchical tags.
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,  # The parent_tag is optional.
        related_name='children',
        help_text="The parent tag in a hierarchical structure (optional)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

        # Ensures that a user cannot have two tags with the same name and parent.
        unique_together = ('user', 'name', 'parent_tag')
        ordering = ['name']

    def __str__(self):
        """
        String representation of the Tag.
        """
        username = self.user.username if self.user else 'guest'
        if self.parent_tag:
            return f"{username}'s Tag: {self.parent_tag.name} > {self.name}"
        return f"{username}'s Tag: {self.name}"


def generate_note_id():
    return f"NOT{str(uuid.uuid4()).upper().replace('-', '')[:15]}"


class Note(models.Model):
    """
    Represents a user's personal note or commentary.
    Notes can be associated with a primary tag.
    """
    id = models.CharField(
        max_length=18,
        default=generate_note_id,
        primary_key=True,
        editable=False,
        help_text="Unique identifier for the note."
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notes',
        null=True,
        blank=True,
        help_text="The user who created this note."
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        # Allows you to get notes from a Tag object (e.g., my_tag.notes.all())
        related_name='notes',
        help_text="A primary tag associated with this note (optional)."
    )

    note_text = models.TextField(
        blank=True, help_text="The actual content of the note."
    )

    public = models.BooleanField(
        default=False,
        help_text="If True, this note is accessible to unauthenticated users."
    )

    # Many-to-many relationship with Verse model, through the NoteVerse
    # intermediary table. This explicit 'through' model is necessary because
    # you have 'note_verses' table in your schema, which implies additional
    # data (like 'id' for the link).
    verses = models.ManyToManyField(
        Verse,
        through='NoteVerse',
        # Allows you to get notes from a Verse object
        # (e.g., my_verse.notes.all())
        related_name='notes',
        help_text="The Bible verses associated with this note."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        # Order by most recent notes first
        ordering = ['-created_at']

    def __str__(self):
        # Display the first 50 characters of the note text
        truncated_text = self.note_text[:50]
        ellipsis = '...' if len(self.note_text) > 50 else ''
        id_display = self.id[:8] if isinstance(self.id, str) else self.id.hex[:8]
        return f"Note (ID: {id_display}): {truncated_text}{ellipsis}"


def generate_note_verse_id():
    return f"NVE{str(uuid.uuid4()).upper().replace('-', '')[:15]}"


class NoteVerse(models.Model):
    """
    Intermediary model for many-to-many relationship between Note and Verse.
    This explicit model corresponds to your 'note_verses' table.
    """
    id = models.CharField(
        max_length=18,
        default=generate_note_verse_id,
        primary_key=True,
        editable=False,
        help_text="Unique identifier for note-verse link."
    )

    note = models.ForeignKey(
        Note,
        # If a note is deleted, its links to verses are also deleted.
        on_delete=models.CASCADE,
        help_text="The note associated with the verse."
    )

    verse = models.ForeignKey(
        Verse,
        on_delete=models.PROTECT,  # Prevent deleting Verses that have Notes
        help_text="The verse associated with the note."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Note-Verse Link"
        verbose_name_plural = "Note-Verse Links"
        # Ensures that a specific note is linked to a specific verse only once.
        # TODO: Refine uniqueness logic
        # unique_together = ('note', 'verse')
        # ordering = ['note', 'verse']

    def __str__(self):
        if isinstance(self.note.id, str):
            note_id_display = self.note.id[:8]
        else:
            note_id_display = self.note.id.hex[:8]
        return f"Link: Note {note_id_display} to Verse {self.verse.id}"
