from django.contrib.auth import get_user_model
from rest_framework import serializers
from bible.models import Verse
from bible.services.dbt.client import get_default_dbt_client
from .models import Note, NoteVerse, Tag
User = get_user_model()


class CurrentAuthenticatedUserDefault:
    """Custom default callable for authenticated user field.
    Returns the current user if authenticated, otherwise the guest user.
    """
    requires_context = True

    def __call__(self, serializer_field):
        request = serializer_field.context.get('request')
        if (request and hasattr(request, 'user') and
                request.user.is_authenticated):
            return request.user
        # Return guest user instead of None
        try:
            return User.objects.get(username='guest')
        except User.DoesNotExist:
            # If guest user doesn't exist, return None
            # The create method will handle this case
            return None


class TagSerializer(serializers.ModelSerializer):
    """Serializes Tag model data for API input and output.
    Includes the 'parent_tag' as its primary key for relationships.
    """
    parent_tag = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        allow_null=True,
        required=False,
        default=None
    )
    user = serializers.HiddenField(
        default=CurrentAuthenticatedUserDefault()
    )
    name = serializers.CharField(max_length=100)

    class Meta:
        model = Tag
        fields = [
            'id', 'user', 'name', 'parent_tag',
            'created_at', 'updated_at',
        ]
        # 'read_only_fields' makes sure 'id', 'created_at', 'updated_at' are
        # automatically handled by Django and not expected in user input.
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'parent_tag': {'default': None}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')

        # Filter parent_tag queryset based on user authentication
        if request and hasattr(request, 'user'):
            if request.user.is_authenticated:
                # For authenticated users, only show their own tags
                self.fields['parent_tag'].queryset = Tag.objects.filter(user=request.user)
            else:
                # For unauthenticated users, only show guest user tags
                try:
                    guest_user = User.objects.get(username='guest')
                    self.fields['parent_tag'].queryset = Tag.objects.filter(user=guest_user)
                except User.DoesNotExist:
                    self.fields['parent_tag'].queryset = Tag.objects.none()

    def create(self, validated_data):
        # If user is None, try to use guest user
        if 'user' in validated_data and validated_data['user'] is None:
            try:
                validated_data['user'] = User.objects.get(username='guest')
            except User.DoesNotExist:
                # If guest user doesn't exist, remove user field
                # to let the model use its default
                validated_data.pop('user')
        return super().create(validated_data)


class NoteVerseReferenceSerializer(serializers.Serializer):
    """Serializer to accept verse details for linking to a Note.
    This is for WRITE operations (e.g., when creating a Note).
    """
    book = serializers.CharField(
        max_length=50,
        help_text="The book name (e.g., 'John')."
    )
    chapter = serializers.IntegerField(
        help_text="The chapter number (e.g., 3)."
    )
    verse = serializers.IntegerField(
        help_text="The verse number (e.g., 16)."
    )


class NoteSerializer(serializers.ModelSerializer):
    """Serializes Note model data.
    - For POST/PUT: Accepts tag UUID and a list of verse
      references (book, chapter, verse).
    - For GET: Displays full tag object and full verse objects.
    """
    tag = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        allow_null=True,
        required=False,
        help_text="UUID of the primary Tag associated with this note."
    )
    user = serializers.HiddenField(
        default=CurrentAuthenticatedUserDefault()
    )
    verse_references = NoteVerseReferenceSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text=(
            "List of objects, each with 'book', 'chapter', and 'verse' "
            "to link to the note."
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')

        # Filter tag queryset based on user authentication
        if request and hasattr(request, 'user'):
            if request.user.is_authenticated:
                # For authenticated users, only show their own tags
                self.fields['tag'].queryset = Tag.objects.filter(user=request.user)
            else:
                # For unauthenticated users, only show guest user tags
                try:
                    guest_user = User.objects.get(username='guest')
                    self.fields['tag'].queryset = Tag.objects.filter(user=guest_user)
                except User.DoesNotExist:
                    self.fields['tag'].queryset = Tag.objects.none()

    class Meta:
        model = Note
        fields = [
            'id', 'user', 'note_text', 'public', 'created_at', 'updated_at',
            'tag', 'verse_references'
        ]

    def create(self, validated_data):
        """
        Overrides the default create method to handle nested verse_references.
        """
        # Pop out the 'verse_references' as it's not a direct field on the Note
        verse_references_data = validated_data.pop('verse_references', [])
        # If user is None, try to use guest user
        if 'user' in validated_data and validated_data['user'] is None:
            try:
                validated_data['user'] = User.objects.get(username='guest')
            except User.DoesNotExist:
                # If guest user doesn't exist, remove user field
                validated_data.pop('user')
        # Create the Note instance using the remaining validated data
        note = Note.objects.create(**validated_data)

        # Handle the many-to-many relationship with verses via NoteVerse
        if verse_references_data:
            note_verse_instances = []
            for verse_ref_data in verse_references_data:
                try:
                    # Attempt to retrieve the Verse instance using
                    # case-insensitive book match
                    verse_instance = Verse.objects.get(
                        book__iexact=verse_ref_data['book'],
                        chapter=verse_ref_data['chapter'],
                        verse=verse_ref_data['verse']
                    )
                    # Create a NoteVerse instance to link the note and verse
                    note_verse_instances.append(
                        NoteVerse(note=note, verse=verse_instance)
                    )
                except Verse.DoesNotExist:
                    error_msg = (
                        f"Verse not found for '{verse_ref_data['book']} "
                        f"{verse_ref_data['chapter']}:"
                        f"{verse_ref_data['verse']}'. "
                        f"Please ensure the verse exists in your database."
                    )
                    raise serializers.ValidationError(error_msg)
                except Exception as e:
                    raise serializers.ValidationError(
                        f"Error processing verse reference: {e}"
                    )

            # Bulk create the intermediary NoteVerse instances for efficiency
            NoteVerse.objects.bulk_create(note_verse_instances)

        return note

    def to_representation(self, instance):
        """
        Overrides the default representation for GET requests to include
        nested tag and verse data with content from DBT API.
        """
        representation = super().to_representation(instance)
        verses = list(instance.verses.all().order_by('verse'))
        if not verses:
            return representation

        dbt_book_id = verses[0].dbt_book_id
        chapter = verses[0].chapter

        verse_numbers = [v.verse for v in verses]
        first_verse_num = verse_numbers[0]
        last_verse_num = verse_numbers[-1]

        kwargs = {
            "verse_start": first_verse_num,
            "verse_end": last_verse_num
        }
        dbt_client = get_default_dbt_client()
        verse_text = dbt_client.get_verses(dbt_book_id, chapter, **kwargs)
        verses_with_text = []

        book_name = verses[0].book

        try:
            for verse in verses:
                matching_verse = next(
                    (v for v in verse_text['data'] if v['verse_start'] == verse.verse),
                    None
                )
                text = matching_verse['verse_text'] if matching_verse else ''
                verse_data = {
                    'book': book_name,
                    'chapter': chapter,
                    'verse': verse.verse,
                    'text': text
                }
                verses_with_text.append(verse_data)
        except Exception as e:
            verse_data['text'] = ''
            print(e)

        representation['verses'] = verses_with_text

        # Include full tag object if a tag exists
        if instance.tag:
            representation['tag'] = TagSerializer(instance.tag).data

        return representation
