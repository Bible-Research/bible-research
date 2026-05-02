from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from bible.services.google_tts.client import QuotaExceeded


@patch("bible.management.commands.generate_chapter_audio.gcs.upload_chapter_artifacts")
@patch("bible.management.commands.generate_chapter_audio.gcs.list_completed_chapters")
@patch("bible.management.commands.generate_chapter_audio.Synthesizer")
def test_command_stops_cleanly_on_quota_exceeded(synth_cls, list_done, upload):
    list_done.return_value = set()
    inst = MagicMock()
    artifacts = MagicMock(
        mp3_bytes=b"x", timestamps_payload={}, duration_seconds=1.0,
    )
    # Two successes, then quota error.
    inst.run.side_effect = [artifacts, artifacts, QuotaExceeded("over")]
    synth_cls.return_value = inst

    out = StringIO()
    call_command("generate_chapter_audio", "--fileset-id", "LVSGLU8", stdout=out)

    assert upload.call_count == 2
    assert "quota_exhausted" in out.getvalue()
