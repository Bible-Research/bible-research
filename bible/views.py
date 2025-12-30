import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.utils.bible_books import get_dbt_book_id
from .serializers import BiblePassageSerializer
from .services.translation_service import TranslationService

logger = logging.getLogger(__name__)


class BiblePassageView(APIView):
    """
    API endpoint to retrieve Bible passages.

    Query Parameters:
        - passage: Book and chapter (e.g., '2 Chronicles 14')
        - response_format: 'text' or 'audio' (default: 'text')
        - fileset_id: The specific DBT fileset ID to use for fetching content.

    Example:
        /api/v1/bible/?passage=John+3&fileset_id=ENGESV
    """

    def get(self, request, format=None):
        passage = request.query_params.get('passage')
        response_format = request.query_params.get(
            'response_format', 'text'
        )
        fileset_id = request.query_params.get('fileset_id', 'ENGESV')

        if not passage:
            return Response(
                {
                    "error": "Passage parameter is required. "
                             "Example: ?passage=John+3:16"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if response_format not in ['text', 'audio']:
            return Response(
                {"error": "Invalid format. Use 'text' or 'audio'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parts = passage.split()
            if len(parts) < 2:
                raise ValueError(
                    "Invalid passage format. "
                    "Use 'Book Chapter' (e.g., 'John 3')"
                )

            # The book name might have spaces (e.g., "1 John")
            chapter_part = parts[-1]
            book_name = ' '.join(parts[:-1])

            # Convert book name to standard book ID
            book_id = get_dbt_book_id(book_name)
            if not book_id:
                raise ValueError(f"Unknown book: {book_name}")

            try:
                chapter = int(chapter_part)
                if chapter <= 0:
                    raise ValueError("Chapter must be a positive number")
            except ValueError:
                raise ValueError("Chapter must be a valid number")

            data = {
                'book': book_id,
                'book_name': book_name,
                'chapter': chapter,
                'format': response_format,
                'fileset_id': fileset_id,
            }

            serializer = BiblePassageSerializer(data=data)
            if serializer.is_valid():
                return Response(serializer.to_representation(data))
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TranslationListView(APIView):
    """
    Lists available Bible translations by fetching live from DBT API.

    Query Parameters:
        - language_iso: Filter by ISO language code
                       (e.g., 'eng', 'lvs')

    Example:
        /api/v1/translations/
        /api/v1/translations/?language_iso=eng
    """

    def get(self, request, *args, **kwargs):
        language_iso = request.query_params.get('language_iso')
        logger.info(f"Request for translations with language_iso: {language_iso}")

        translations = TranslationService.get_live_translations(language_iso)
        logger.info(f"Found {len(translations)} translations for language_iso: {language_iso}")

        # Prepare response with detailed fileset information
        response_data = [
            {
                'abbr': t['abbr'],
                'name': t['name'],
                'language': t['language'],
                'language_iso': t['iso'],
                'filesets': t['filesets'],
            }
            for t in translations
        ]
        logger.debug(f"Returning response data: {response_data}")
        return Response({'results': response_data})
