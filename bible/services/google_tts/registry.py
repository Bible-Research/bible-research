"""Per-fileset TTS configuration. Keys mirror SWORD_TRANSLATIONS."""
from django.conf import settings

from bible.services.sword.registry import canonical_sword_fileset_id


def get_tts_config(canonical_fileset_id: str) -> dict:
    """Return the TTS config for a canonical SWORD fileset id.

    Accepts both canonical ids (e.g. LVSGLU8) and audio fileset ids
    (e.g. LVSGLU8C1DA); the latter are resolved to the canonical key
    first. Currently only LVSGLU8 is supported; the values come from
    settings so the Cloud Run Job can override them via env vars."""
    canon = canonical_sword_fileset_id(canonical_fileset_id)
    if canon != "LVSGLU8":
        raise KeyError(canonical_fileset_id)
    return {
        "language_code": settings.GOOGLE_TTS_LANGUAGE_CODE,
        "voice_name": settings.GOOGLE_TTS_VOICE_NAME,
        "sample_rate_hertz": settings.GOOGLE_TTS_SAMPLE_RATE_HERTZ,
    }
