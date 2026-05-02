"""Thin wrapper around google.cloud.texttospeech."""
import threading
from typing import Optional

from google.api_core import exceptions as gax
from google.cloud import texttospeech


class QuotaExceeded(Exception):
    """Raised when Cloud TTS reports the project's quota is depleted."""


class GoogleTTSClient:
    def __init__(self, client: Optional[texttospeech.TextToSpeechClient] = None):
        self._client = client or texttospeech.TextToSpeechClient()

    def synthesize_text(
        self,
        text: str,
        language_code: str,
        voice_name: str,
        sample_rate_hertz: int = 24000,
    ) -> bytes:
        request = texttospeech.SynthesizeSpeechRequest(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                sample_rate_hertz=sample_rate_hertz,
            ),
        )
        try:
            response = self._client.synthesize_speech(request=request)
        except gax.ResourceExhausted as exc:
            raise QuotaExceeded(str(exc)) from exc
        return response.audio_content


_default: Optional[GoogleTTSClient] = None
_default_lock = threading.Lock()


def get_default_tts_client() -> GoogleTTSClient:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = GoogleTTSClient()
    return _default
