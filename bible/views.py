import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.utils.bible_books import get_dbt_book_id
from bible.services.sword.registry import is_sword_fileset
from .serializers import BiblePassageSerializer
from .services.translation_service import TranslationService
from .services.dbt.client import get_default_dbt_client

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
        /api/v1/bible/?passage=John+3&fileset_id=LVSGLU8   # Latvian Glück
    """

    def get(self, request, format=None):
        passage = request.query_params.get('passage')
        response_format = request.query_params.get(
            'response_format', 'text'
        )
        fileset_id = request.query_params.get('fileset_id', 'ENGESV')

        logger.info(
            f"BiblePassageView.get called with passage: {passage}, "
            f"format: {response_format}, fileset_id: {fileset_id}"
        )

        if not passage:
            logger.warning("Request missing required 'passage' parameter")
            return Response(
                {
                    "error": "Passage parameter is required. "
                             "Example: ?passage=John+3:16"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if response_format not in ['text', 'audio']:
            logger.warning(
                f"Invalid response_format: {response_format}"
            )
            return Response(
                {"error": "Invalid format. Use 'text' or 'audio'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if response_format == 'audio' and is_sword_fileset(fileset_id):
            return Response(
                {"error": "Audio not available for this translation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logger.debug(f"Parsing passage: {passage}")
            parts = passage.split()
            if len(parts) < 2:
                logger.error(
                    f"Invalid passage format: {passage} "
                    f"(parts: {parts})"
                )
                raise ValueError(
                    "Invalid passage format. "
                    "Use 'Book Chapter' (e.g., 'John 3')"
                )

            # The book name might have spaces (e.g., "1 John")
            chapter_part = parts[-1]
            book_name = ' '.join(parts[:-1])
            logger.debug(
                f"Extracted book_name: {book_name}, "
                f"chapter_part: {chapter_part}"
            )

            # Convert book name to standard book ID
            book_id = get_dbt_book_id(book_name)
            if not book_id:
                logger.error(f"Unknown book name: {book_name}")
                raise ValueError(f"Unknown book: {book_name}")
            logger.debug(f"Resolved book_id: {book_id}")

            try:
                chapter = int(chapter_part)
                if chapter <= 0:
                    logger.error(
                        f"Invalid chapter number: {chapter} "
                        f"(must be positive)"
                    )
                    raise ValueError(
                        "Chapter must be a positive number"
                    )
                logger.debug(f"Parsed chapter number: {chapter}")
            except ValueError as ve:
                logger.error(
                    f"Failed to parse chapter: {chapter_part} - {ve}"
                )
                raise ValueError("Chapter must be a valid number")

            data = {
                'book': book_id,
                'book_name': book_name,
                'chapter': chapter,
                'format': response_format,
                'fileset_id': fileset_id,
            }
            logger.debug(f"Prepared data for serializer: {data}")

            serializer = BiblePassageSerializer(data=data)
            if serializer.is_valid():
                logger.info(
                    f"Successfully retrieved passage: "
                    f"{book_name} {chapter} ({fileset_id})"
                )
                return Response(serializer.to_representation(data))

            logger.error(
                f"Serializer validation failed: {serializer.errors}"
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception(
                f"Error processing Bible passage request: {passage} - {e}"
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AudioTimestampView(APIView):
    """Return audio timestamps for a chapter."""

    def get(self, request, format=None):
        fileset_id = request.query_params.get('fileset_id')
        book = request.query_params.get('book')
        chapter = request.query_params.get('chapter')

        if not all([fileset_id, book, chapter]):
            return Response(
                {
                    "error":
                    "fileset_id, book, and chapter "
                    "are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Convert book name to DBT book ID
            # (e.g. "John" -> "JHN")
            book_id = get_dbt_book_id(book)
            if not book_id:
                return Response(
                    {"error": f"Unknown book: {book}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            dbt_client = get_default_dbt_client()
            result = dbt_client.get_timestamps(
                fileset_id, book_id, chapter
            )
            timestamps = [
                {
                    "verse_start": item.get(
                        "verse_start"
                    ),
                    "timestamp": item.get(
                        "timestamp"
                    ),
                }
                for item in result.get("data", [])
            ]
            return Response({"data": timestamps})
        except Exception as e:
            logger.exception(
                "Error fetching timestamps: %s", e
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CopyrightView(APIView):
    """Return copyright info for a Bible translation."""

    def get(self, request, format=None):
        bible_id = request.query_params.get('bible_id')

        if not bible_id:
            return Response(
                {"error": "bible_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dbt_client = get_default_dbt_client()
            result = dbt_client.get_copyright(bible_id)

            filesets = []
            for item in (result or []):
                cr = item.get("copyright") or {}
                filesets.append({
                    "id": item.get("id"),
                    "type": item.get("type"),
                    "size": item.get("size"),
                    "copyright": cr.get("copyright", ""),
                    "copyright_date": cr.get(
                        "copyright_date", ""
                    ),
                    "copyright_description": cr.get(
                        "copyright_description", ""
                    ),
                })
            return Response({"data": filesets})
        except Exception as e:
            logger.exception(
                "Error fetching copyright: %s", e
            )
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
        logger.info(
            f"TranslationListView.get called with "
            f"language_iso: {language_iso or 'all'}"
        )

        try:
            translations = TranslationService.get_live_translations(
                language_iso
            )
            logger.info(
                f"Found {len(translations)} translations "
                f"for language_iso: {language_iso or 'all'}"
            )

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
            logger.debug(
                f"Returning {len(response_data)} translations"
            )
            return Response({'results': response_data})

        except Exception as e:
            logger.exception(
                f"Error fetching translations for "
                f"language_iso: {language_iso} - {e}"
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
