from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import BiblePassageSerializer
from bible.utils.bible_books import get_dbt_book_id


class BiblePassageView(APIView):
    """
    API endpoint to retrieve Bible passages.

    Query Parameters:
        - passage: Book and chapter (e.g., '2 Chronicles 14')
        - response_format: 'text' or 'audio' (default: 'text')
        - translation: Bible translation code
                       (e.g., 'ENGESV', default: 'ENGESV')
        - audio_type: Audio type - '1DA' for audio, '2DA' for
                      audio drama (default: '2DA')

    Example:
        /api/v1/bible/?passage=2%20Chronicles%2014&translation=ENGESV
    """

    def get(self, request, format=None):
        passage = request.query_params.get('passage')
        response_format = request.query_params.get(
            'response_format', 'text'
        )
        translation = request.query_params.get('translation', 'ENGESV')
        audio_type = request.query_params.get('audio_type', '2DA')

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
                'translation': translation,
                'audio_type': audio_type,
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
