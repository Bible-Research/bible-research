import logging
import time
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
        start_time = time.time()
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

            serializer_start = time.time()
            serializer = BiblePassageSerializer(data=data)
            if serializer.is_valid():
                logger.info(
                    f"Successfully retrieved passage: "
                    f"{book_name} {chapter} ({fileset_id})"
                )
                response = Response(serializer.to_representation(data))
                serializer_end = time.time()
                total_time = time.time() - start_time
                logger.info(
                    f"API call timing - Total: {total_time:.3f}s, "
                    f"Serializer: {serializer_end - serializer_start:.3f}s"
                )
                return response

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
