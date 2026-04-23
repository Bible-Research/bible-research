import pytest
from unittest.mock import Mock, patch
from bible.services.dbt.client import DBTClient


@pytest.fixture
def dbt_client():
    """Fixture to provide a DBTClient instance."""
    return DBTClient()


@patch('bible.services.dbt.client.requests.get')
def test_get_timestamps_calls_api(mock_get, dbt_client):
    """
    Test that get_timestamps calls requests.get with the
    correct URL and parameters.
    """
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {"verse_start": 1, "timestamp": 0.0},
            {"verse_start": 2, "timestamp": 5.5},
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    fileset_id = "ENGESVN2DA"
    book = "JHN"
    chapter = "1"

    result = dbt_client.get_timestamps(fileset_id, book, chapter)

    mock_get.assert_called_once()
    call_args, call_kwargs = mock_get.call_args
    assert 'v=4' in call_args[0] or call_kwargs.get(
        'params', {}
    ).get('v') == 4
    assert result == {
        "data": [
            {"verse_start": 1, "timestamp": 0.0},
            {"verse_start": 2, "timestamp": 5.5},
        ]
    }


@patch('bible.services.dbt.client.requests.get')
def test_get_timestamps_injects_version(mock_get, dbt_client):
    """
    Test that get_timestamps passes v=4 as a query parameter.
    """
    mock_response = Mock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    dbt_client.get_timestamps("fileset", "book", "chapter")

    call_args, call_kwargs = mock_get.call_args
    params = call_kwargs.get('params', {})
    assert params.get('v') == 4
