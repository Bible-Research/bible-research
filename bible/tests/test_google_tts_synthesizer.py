from unittest.mock import patch

from bible.services.google_tts.synthesizer import Synthesizer


class _FakeMP3Info:
    def __init__(self, length):
        self.length = length


class _FakeMP3:
    def __init__(self, _stream):
        self.info = _FakeMP3Info(2.0)


@patch("bible.services.google_tts.synthesizer.MP3", _FakeMP3)
def test_synthesizer_builds_cumulative_timestamps():
    fake_audio = b"\xff\xfb" + b"\x00" * 100  # opaque bytes; MP3 mocked

    class FakeTTS:
        def synthesize_text(self, text, **_):
            return fake_audio

    synth = Synthesizer(tts_client=FakeTTS())
    artifacts = synth.run("LVSGLU8", "JHN", 3)

    payload = artifacts.timestamps_payload
    assert payload["data"][0]["verse_start"] == 1
    assert payload["data"][0]["timestamp"] == 0.0
    # Each verse = 2.0s by the MP3 mock; verse 2 starts at 2.0s
    assert payload["data"][1]["timestamp"] == 2.0
    # MP3 bytes are concatenated
    assert artifacts.mp3_bytes.startswith(fake_audio)
    assert len(artifacts.mp3_bytes) == len(fake_audio) * len(payload["data"])
