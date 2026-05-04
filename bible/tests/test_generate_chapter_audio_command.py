from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from bible.services.google_tts.client import QuotaExceeded


@patch("bible.management.commands.generate_chapter_audio.gcs.mark_run_complete")
@patch("bible.management.commands.generate_chapter_audio.gcs.increment_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.read_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.acquire_run_lock")
@patch("bible.management.commands.generate_chapter_audio.gcs.upload_chapter_artifacts")
@patch("bible.management.commands.generate_chapter_audio.gcs.list_completed_chapters")
@patch("bible.management.commands.generate_chapter_audio.Synthesizer")
def test_command_stops_cleanly_on_quota_exceeded(
    synth_cls, list_done, upload, acquire, read_usage, increment, mark_complete,
):
    acquire.return_value = (True, "acquired")
    read_usage.return_value = 0
    list_done.return_value = set()
    inst = MagicMock()
    artifacts = MagicMock(
        mp3_bytes=b"x", timestamps_payload={}, duration_seconds=1.0,
        chars_used=50,
    )

    # The real synthesizer consumes budget per-verse as Cloud TTS
    # bills us; the command now relies on that side effect to compute
    # the per-chapter usage delta it persists to GCS.
    call_outcomes = [artifacts, artifacts, QuotaExceeded("over")]

    def fake_run(_fileset, _book, _chap, budget=None):
        outcome = call_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if budget is not None:
            budget.consume(outcome.chars_used)
        return outcome

    inst.run.side_effect = fake_run
    synth_cls.return_value = inst

    out = StringIO()
    call_command("generate_chapter_audio", "--fileset-id", "LVSGLU8", stdout=out)

    assert upload.call_count == 2
    assert increment.call_count == 2
    assert "quota_exhausted" in out.getvalue()
    mark_complete.assert_called_once()
    assert mark_complete.call_args.kwargs["reason"] == "quota_exhausted"


@patch("bible.management.commands.generate_chapter_audio.gcs.mark_run_complete")
@patch("bible.management.commands.generate_chapter_audio.gcs.increment_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.read_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.acquire_run_lock")
@patch("bible.management.commands.generate_chapter_audio.gcs.upload_chapter_artifacts")
@patch("bible.management.commands.generate_chapter_audio.gcs.list_completed_chapters")
@patch("bible.management.commands.generate_chapter_audio.Synthesizer")
def test_partial_chapter_billed_chars_are_persisted_on_quota_error(
    synth_cls, list_done, upload, acquire, read_usage, increment,
    mark_complete,
):
    """Regression: if Cloud TTS raises QuotaExceeded partway through a
    chapter, the characters it already billed us for (reflected in
    ``budget.used``) must still be persisted to GCS. Otherwise the
    next run would read a stale counter and exceed the monthly cap."""
    acquire.return_value = (True, "acquired")
    read_usage.return_value = 0
    list_done.return_value = set()

    inst = MagicMock()

    def run_side_effect(_fileset, _book, _chap, budget=None):
        # Simulate 3 billed verses, then TTS quota dies on verse 4.
        for _ in range(3):
            budget.consume(40)
        raise QuotaExceeded("mid-chapter")

    inst.run.side_effect = run_side_effect
    synth_cls.return_value = inst

    out = StringIO()
    call_command(
        "generate_chapter_audio", "--fileset-id", "LVSGLU8", stdout=out,
    )

    # Nothing uploaded (chapter never completed), but the 120 chars
    # Google already billed MUST be written to the GCS usage counter.
    assert upload.call_count == 0
    assert increment.call_count == 1
    assert increment.call_args.args[1] == 120
    assert "quota_exhausted" in out.getvalue()
    mark_complete.assert_called_once()
    assert mark_complete.call_args.kwargs["chars_used"] == 120


@patch("bible.management.commands.generate_chapter_audio.gcs.mark_run_complete")
@patch("bible.management.commands.generate_chapter_audio.gcs.increment_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.read_monthly_usage")
@patch("bible.management.commands.generate_chapter_audio.gcs.acquire_run_lock")
@patch("bible.management.commands.generate_chapter_audio.gcs.upload_chapter_artifacts")
@patch("bible.management.commands.generate_chapter_audio.gcs.list_completed_chapters")
@patch("bible.management.commands.generate_chapter_audio.Synthesizer")
def test_billed_chars_persisted_when_upload_fails(
    synth_cls, list_done, upload, acquire, read_usage, increment,
    mark_complete,
):
    """Regression: a successfully-synthesized chapter whose upload
    fails still cost us Cloud TTS characters. Those chars must land in
    the monthly usage counter so a persistent upload outage cannot
    silently drive us over ``MONTHLY_TTS_CHAR_LIMIT``."""
    acquire.return_value = (True, "acquired")
    read_usage.return_value = 0
    list_done.return_value = set()
    upload.side_effect = RuntimeError("gcs 503")

    inst = MagicMock()

    def run_side_effect(_fileset, _book, _chap, budget=None):
        budget.consume(75)
        return MagicMock(
            mp3_bytes=b"x", timestamps_payload={"data": []},
            duration_seconds=1.0, chars_used=75,
        )

    # First chapter synthesizes successfully (but upload fails below);
    # second call raises QuotaExceeded to terminate the run promptly.
    outcomes = [run_side_effect, QuotaExceeded("stop")]

    def dispatch(fileset, book, chap, budget=None):
        nxt = outcomes.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt(fileset, book, chap, budget=budget)

    inst.run.side_effect = dispatch
    synth_cls.return_value = inst

    call_command("generate_chapter_audio", "--fileset-id", "LVSGLU8")

    # Upload was attempted and failed, but the 75 billed chars must
    # still be persisted.
    assert upload.call_count == 1
    assert increment.call_count == 1
    assert increment.call_args.args[1] == 75
