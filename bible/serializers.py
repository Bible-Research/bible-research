import logging
from rest_framework import serializers

from bible.services.dbt.client import get_default_dbt_client
from bible.services.sword.client import get_default_sword_client
from bible.services.sword.registry import is_sword_fileset


logger = logging.getLogger(__name__)


class BiblePassageSerializer(serializers.Serializer):
    book = serializers.CharField(
      required=True,
      help_text="Standard book ID (e.g., '2CH')"
    )
    book_name = serializers.CharField(
      required=False,
      help_text="Full book name (e.g., '2 Chronicles)'"
    )
    chapter = serializers.IntegerField(
      required=True,
      min_value=1,
      help_text="Chapter number"
    )
    fileset_id = serializers.CharField(
      required=True,
      help_text="DBT fileset ID for the specific translation and format"
    )

    def to_representation(self, instance):
        book_id = instance.get('book')
        book_name = instance.get('book_name', '')
        chapter = int(instance.get('chapter'))
        fileset_id = instance.get('fileset_id')

        try:
            if is_sword_fileset(fileset_id):
                verses = get_default_sword_client().get_chapter_verses(
                    fileset_id, book_id, chapter
                )
                return {
                    'book': book_id,
                    'book_name': book_name,
                    'chapter': chapter,
                    'format': 'text',
                    'verses': [
                        {'verse': v['verse_start'], 'text': v['verse_text']}
                        for v in verses
                    ],
                }

            dbt_client = get_default_dbt_client()
            passage_data = dbt_client.get_verses(
                book_id, str(chapter), bible_id=fileset_id
            )
            audio_format = 'path' in passage_data['data'][0]
            if audio_format:
                audio_data = passage_data['data'][0]
                return {
                    'book': book_id,
                    'book_name': book_name,
                    'chapter': chapter,
                    'audio_url': audio_data.get('path'),
                    'duration_seconds': audio_data.get('duration'),
                    'file_size_bytes': audio_data.get('filesize_in_bytes'),
                    'format': 'audio',
                }
            return {
                'book': book_id,
                'book_name': book_name,
                'chapter': chapter,
                'format': 'text',
                'verses': [
                    {'verse': v['verse_start'], 'text': v.get('verse_text', '')}
                    for v in passage_data['data']
                    if 'verse_text' in v
                ],
            }
        except Exception as e:
            logger.error(f"Error fetching Bible passage: {str(e)}")
            return {
                'book': book_id,
                'book_name': book_name,
                'chapter': chapter,
                'verses': [],
                'message': 'No verses found for the specified passage',
            }
