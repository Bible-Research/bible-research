import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIRequestFactory

from bible.views import BibleSearchView


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.mark.django_db
def test_missing_query_param(factory):
    """Missing query → 400 with descriptive error."""
    request = factory.get(
        '/fake-url/', {'fileset_id': 'ENGESV'}
    )
    response = BibleSearchView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'query' in response.data['error']


@pytest.mark.django_db
def test_missing_fileset_id_param(factory):
    """Missing fileset_id → 400 with descriptive error."""
    request = factory.get(
        '/fake-url/', {'query': 'love'}
    )
    response = BibleSearchView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'fileset_id' in response.data['error']


@pytest.mark.django_db
@patch('bible.views.is_sword_fileset', return_value=False)
@patch('bible.views.get_default_dbt_client')
def test_dbt_search_proxies_with_params(
    mock_get_client, mock_is_sword, factory
):
    """DBT fileset → search() called with limit and books."""
    mock_get_client.return_value.search.return_value = {
        'verses': {
            'data': [
                {
                    'book_id': 'JHN',
                    'chapter': 3,
                    'verse_start': 16,
                    'verse_text': 'For God so loved the world',
                }
            ]
        },
        'meta': {'pagination': {'total': 1}},
    }

    request = factory.get('/fake-url/', {
        'query': 'loved',
        'fileset_id': 'ENGESV',
        'limit': '5',
        'books': 'JHN',
    })
    response = BibleSearchView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK
    verses = response.data['data']['verses']
    assert len(verses) == 1
    assert verses[0]['book_id'] == 'JHN'
    assert verses[0]['verse_start'] == 16

    mock_get_client.return_value.search.assert_called_once_with(
        'ENGESV', 'loved',
        limit=5, page=1,
        sort_by=None, books='JHN',
    )


@pytest.mark.django_db
@patch('bible.views.is_sword_fileset', return_value=True)
@patch('bible.views.get_default_sword_client')
def test_sword_search_filters_by_query(
    mock_get_sword, mock_is_sword, factory
):
    """SWORD fileset → verses filtered by query substring."""
    mock_sword = mock_get_sword.return_value
    mock_sword.list_chapters.return_value = [
        ('GEN', 1), ('GEN', 2)
    ]
    mock_sword.get_chapter_verses.side_effect = [
        [
            {'verse_start': 1, 'verse_text': 'In the beginning'},
            {'verse_start': 2, 'verse_text': 'darkness over the deep'},
        ],
        [
            {'verse_start': 1, 'verse_text': 'No match here'},
        ],
    ]

    request = factory.get('/fake-url/', {
        'query': 'beginning',
        'fileset_id': 'LVSGLU8',
    })
    response = BibleSearchView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK
    verses = response.data['data']['verses']
    assert len(verses) == 1
    assert verses[0]['verse_start'] == 1
    assert verses[0]['book_id'] == 'GEN'
    assert verses[0]['chapter'] == 1
    pagination = response.data['data']['meta']['pagination']
    assert pagination['total'] == 1


@pytest.mark.django_db
@patch('bible.views.is_sword_fileset', return_value=True)
@patch('bible.views.get_default_sword_client')
def test_sword_books_filter_limits_scan(
    mock_get_sword, mock_is_sword, factory
):
    """SWORD books filter → only chapters from listed books scanned."""
    mock_sword = mock_get_sword.return_value
    mock_sword.list_chapters.return_value = [
        ('GEN', 1), ('EXO', 1), ('MAT', 1)
    ]
    mock_sword.get_chapter_verses.return_value = [
        {'verse_start': 1, 'verse_text': 'love'}
    ]

    request = factory.get('/fake-url/', {
        'query': 'love',
        'fileset_id': 'LVSGLU8',
        'books': 'GEN,MAT',
    })
    response = BibleSearchView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK
    assert mock_sword.get_chapter_verses.call_count == 2
    called_books = {
        call.args[1]
        for call in mock_sword.get_chapter_verses.call_args_list
    }
    assert called_books == {'GEN', 'MAT'}
