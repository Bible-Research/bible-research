import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APIRequestFactory

from bible.views import AudioTimestampView
from bible.services.dbt.client import DBTClient


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.mark.django_db
@patch('bible.views.DBTClient')
def test_get_timestamps_success(MockDBTClient, factory):
    """Test successful retrieval of timestamps."""
    mock_dbt_instance = MockDBTClient.return_value
    mock_dbt_instance.get_timestamps.return_value = {
        "data": [
            {"verse_start": 1, "timestamp": 0.0},
            {"verse_start": 2, "timestamp": 5.5},
        ]
    }

    request = factory.get('/fake-url/', {
        'fileset_id': 'ENGESVN2DA',
        'book': 'JHN',
        'chapter': '1'
    })
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['data']) == 2
    assert response.data['data'][0]['verse_start'] == 1


@pytest.mark.django_db
def test_get_timestamps_missing_params(factory):
    """Test request with missing query parameters."""
    request = factory.get('/fake-url/', {'book': 'JHN', 'chapter': '1'})
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data


@pytest.mark.django_db
@patch('bible.views.DBTClient')
def test_get_timestamps_dbt_exception(MockDBTClient, factory):
    """Test handling of an exception from the DBT client."""
    mock_dbt_instance = MockDBTClient.return_value
    mock_dbt_instance.get_timestamps.side_effect = Exception("DBT Error")

    request = factory.get('/fake-url/', {
        'fileset_id': 'ENGESVN2DA',
        'book': 'JHN',
        'chapter': '1'
    })
    view = AudioTimestampView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data
    assert response.data['error'] == "DBT Error"
