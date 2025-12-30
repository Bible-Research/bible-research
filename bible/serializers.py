import logging
from rest_framework import serializers
from bible.services.dbt.client import DBTClient


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
        dbt_client = DBTClient()
        book_id = instance.get('book')
        book_name = instance.get('book_name', '')
        chapter = str(instance.get('chapter'))
        fileset_id = instance.get('fileset_id')

        try:
            passage_data = dbt_client.get_verses(
              book_id,
              chapter,
              bible_id=fileset_id
            )

            audio_format = 'path' in passage_data['data'][0]

            if audio_format:
                audio_data = passage_data['data'][0]
                response_data = {
                    'book': book_id,
                    'book_name': book_name,
                    'chapter': int(chapter),
                    'audio_url': audio_data.get('path'),
                    'duration_seconds': audio_data.get('duration'),
                    'file_size_bytes': audio_data.get('filesize_in_bytes'),
                    'format': 'audio'
                }
            else:
                response_data = {
                    'book': book_id,
                    'book_name': book_name,
                    'chapter': int(chapter),
                    'format': 'text',
                    'verses': [
                        {
                            'verse': verse['verse_start'],
                            'text': verse.get('verse_text', '')
                        }
                        for verse in passage_data['data']
                        if 'verse_text' in verse
                    ]
                }

            return response_data

        except Exception as e:
            logger.error(f"Error fetching Bible passage: {str(e)}")
            return {
                'book': book_id,
                'book_name': book_name,
                'chapter': int(chapter),
                'verses': [],
                'message': 'No verses found for the specified passage'
            }
