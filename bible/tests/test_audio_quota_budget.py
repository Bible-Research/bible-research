from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.test import override_settings

from bible.services.google_tts.budget import BudgetExceeded, CharBudget


def test_char_budget_basic():
    b = CharBudget(remaining=100)
    assert b.can_afford(60)
    b.consume(60)
    assert b.remaining == 40
    assert b.used == 60
    with pytest.raises(BudgetExceeded):
        b.consume(50)


@override_settings(MONTHLY_TTS_CHAR_LIMIT=300, LOCK_STALE_HOURS=24)
@patch("bible.management.commands.generate_chapter_audio.gcs.mark_run_complete")
@patch("bible.management.commands.generate_chapter_audio.gcs.increment_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.read_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.acquire_run_lock")
@patch("bible.management.commands.generate_chapter_audio.gcs.list_completed_chapters")
@patch("bible.management.commands.generate_chapter_audio.gcs.upload_chapter_artifacts")
@patch("bible.management.commands.generate_chapter_audio.Synthesizer")
def test_command_stops_when_budget_too_small_for_next_chapter(
    synth_cls, upload, list_done, acquire, read_usage, increment, mark_done,
):
    acquire.return_value = (True, "acquired")
    read_usage.return_value = 0
    list_done.return_value = set()

    inst = MagicMock()

    def run_side_effect(fileset_id, book_id, chap, budget=None):
        if budget is None:
            raise AssertionError("budget must be passed")
        if budget.remaining >= 200:
            budget.consume(200)
            return MagicMock(
                mp3_bytes=b"x", timestamps_payload={"data": []},
                duration_seconds=1.0, chars_used=200,
            )
        raise BudgetExceeded("not enough")

    inst.run.side_effect = run_side_effect
    synth_cls.return_value = inst

    out = StringIO()
    call_command(
        "generate_chapter_audio", "--fileset-id", "LVSGLU8", stdout=out,
    )

    assert upload.call_count == 1
    assert increment.call_count == 1
    assert increment.call_args.args[1] == 200
    assert "budget_exhausted" in out.getvalue()
    mark_done.assert_called_once()
    assert mark_done.call_args.kwargs["reason"] == "budget_exhausted"
