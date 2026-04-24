import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIRequestFactory

from bible.views import AudioTimestampView


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.mark.django_db
@patch('bible.views.get_default_dbt_client')
@patch('bible.views.get_dbt_book_id')
def test_get_timestamps_success(
    mock_get_dbt_book_id, mock_get_client, factory
):
    """Test successful retrieval of timestamps."""
    mock_get_dbt_book_id.return_value = 'JHN'
    mock_dbt_instance = mock_get_client.return_value
    mock_dbt_instance.get_timestamps.return_value = {
        "data": [
            {"verse_start": 1, "timestamp": 0.0},
            {"verse_start": 2, "timestamp": 5.5},
        ]
    }

    request = factory.get('/fake-url/', {
        'fileset_id': 'ENGESVN2DA',
        'book': 'John',
        'chapter': '1'
    })
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['data']) == 2
    assert response.data['data'][0]['verse_start'] == 1
    mock_get_dbt_book_id.assert_called_once_with('John')
    mock_dbt_instance.get_timestamps.assert_called_once_with(
        'ENGESVN2DA', 'JHN', '1'
    )


@pytest.mark.django_db
def test_get_timestamps_missing_params(factory):
    """Test request with missing query parameters."""
    request = factory.get(
        '/fake-url/', {'book': 'John', 'chapter': '1'}
    )
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data


@pytest.mark.django_db
@patch('bible.views.get_default_dbt_client')
@patch('bible.views.get_dbt_book_id')
def test_get_timestamps_dbt_exception(
    mock_get_dbt_book_id, mock_get_client, factory
):
    """Test handling of an exception from the DBT client."""
    mock_get_dbt_book_id.return_value = 'JHN'
    mock_dbt_instance = mock_get_client.return_value
    mock_dbt_instance.get_timestamps.side_effect = Exception(
        "DBT Error"
    )

    request = factory.get('/fake-url/', {
        'fileset_id': 'ENGESVN2DA',
        'book': 'John',
        'chapter': '1'
    })
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data
    assert response.data['error'] == "DBT Error"


@pytest.mark.django_db
def test_get_timestamps_unknown_book(factory):
    """Test request with an unknown book name."""
    request = factory.get('/fake-url/', {
        'fileset_id': 'ENGESVN2DA',
        'book': 'UnknownBook',
        'chapter': '1'
    })
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Unknown book' in response.data['error']
