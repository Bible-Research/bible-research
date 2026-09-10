"""Pagination classes for annotations app."""

from rest_framework.pagination import PageNumberPagination


class NotesPagination(PageNumberPagination):
    """
    Pagination class for notes with configurable page size.

    Default: 25 notes per page
    Max: 100 notes per page

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 25, max: 100)
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
