from unittest.mock import patch

import pytest

from bible.services.storage import gcs


class _FakeBlob:
    def __init__(self, name, store):
        self.name = name
        self._store = store
        self.generation = 0

    def exists(self):
        return self.name in self._store

    def reload(self):
        self.generation = self._store[self.name]["gen"]

    def download_as_bytes(self):
        return self._store[self.name]["data"]

    def upload_from_string(self, data, content_type=None, if_generation_match=None):
        existing = self._store.get(self.name)
        if if_generation_match == 0 and existing is not None:
            from google.api_core import exceptions as gax
            raise gax.PreconditionFailed("exists")
        if (
            if_generation_match is not None
            and if_generation_match != 0
            and (existing is None or existing["gen"] != if_generation_match)
        ):
            from google.api_core import exceptions as gax
            raise gax.PreconditionFailed("gen mismatch")
        new_gen = (existing["gen"] + 1) if existing else 1
        self._store[self.name] = {
            "data": data.encode() if isinstance(data, str) else data,
            "gen": new_gen,
        }
        self.generation = new_gen


class _FakeBucket:
    def __init__(self):
        self._store = {}
        self.name = "fake-bucket"

    def blob(self, name):
        return _FakeBlob(name, self._store)


@pytest.fixture
def fake_bucket():
    bucket = _FakeBucket()
    with patch.object(gcs, "_bucket", return_value=bucket):
        yield bucket


def test_acquire_lock_first_time_succeeds(fake_bucket):
    ok, reason = gcs.acquire_run_lock("LVSGLU8", stale_after_hours=24)
    assert ok and reason == "acquired"


def test_second_acquire_within_stale_window_fails(fake_bucket):
    gcs.acquire_run_lock("LVSGLU8", stale_after_hours=24)
    ok, reason = gcs.acquire_run_lock("LVSGLU8", stale_after_hours=24)
    assert not ok and reason == "active_run"


def test_completed_lock_blocks_reentry(fake_bucket):
    gcs.acquire_run_lock("LVSGLU8", stale_after_hours=24)
    gcs.mark_run_complete(
        "LVSGLU8", chars_used=10, chapters_generated=1, reason="all_done",
    )
    ok, reason = gcs.acquire_run_lock("LVSGLU8", stale_after_hours=24)
    assert not ok and reason == "already_completed"


def test_increment_monthly_usage_round_trip(fake_bucket):
    assert gcs.read_monthly_usage("LVSGLU8") == 0
    assert gcs.increment_monthly_usage("LVSGLU8", 1500) == 1500
    assert gcs.increment_monthly_usage("LVSGLU8", 250) == 1750
    assert gcs.read_monthly_usage("LVSGLU8") == 1750
