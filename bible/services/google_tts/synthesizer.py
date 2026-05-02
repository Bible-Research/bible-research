"""Per-chapter audio synthesis: SWORD verses -> Cloud TTS -> MP3 + timestamps."""
import io
from dataclasses import dataclass
from typing import Optional

from mutagen.mp3 import MP3

from bible.services.sword.client import get_default_sword_client
from bible.services.sword.registry import canonical_sword_fileset_id

from .budget import BudgetExceeded, CharBudget
from .client import GoogleTTSClient, get_default_tts_client
from .registry import get_tts_config


@dataclass
class ChapterArtifacts:
    mp3_bytes: bytes
    timestamps_payload: dict
    duration_seconds: float
    chars_used: int


class Synthesizer:
    def __init__(self, tts_client: Optional[GoogleTTSClient] = None):
        self._tts = tts_client or get_default_tts_client()
        self._sword = get_default_sword_client()

    def run(
        self,
        fileset_id: str,
        book_id: str,
        chapter: int,
        budget: CharBudget | None = None,
    ) -> ChapterArtifacts:
        canon = canonical_sword_fileset_id(fileset_id)
        if not canon:
            raise ValueError(f"Unknown SWORD fileset: {fileset_id!r}")
        cfg = get_tts_config(canon)

        verses = self._sword.get_chapter_verses(canon, book_id, chapter)
        if not verses:
            raise ValueError(
                f"No verses for {book_id} {chapter} in {canon}"
            )

        chapter_chars = sum(len(v["verse_text"]) for v in verses)
        if budget is not None and not budget.can_afford(chapter_chars):
            raise BudgetExceeded(
                f"chapter {book_id} {chapter} needs {chapter_chars} chars, "
                f"only {budget.remaining} remain"
            )

        chunks: list[bytes] = []
        timestamps: list[dict] = []
        cumulative = 0.0
        for v in verses:
            audio = self._tts.synthesize_text(
                text=v["verse_text"],
                language_code=cfg["language_code"],
                voice_name=cfg["voice_name"],
                sample_rate_hertz=cfg["sample_rate_hertz"],
            )
            duration = float(MP3(io.BytesIO(audio)).info.length)
            timestamps.append({
                "verse_start": v["verse_start"],
                "timestamp": round(cumulative, 3),
            })
            cumulative += duration
            chunks.append(audio)

        if budget is not None:
            budget.consume(chapter_chars)

        return ChapterArtifacts(
            mp3_bytes=b"".join(chunks),
            timestamps_payload={
                "duration_seconds": round(cumulative, 3),
                "data": timestamps,
            },
            duration_seconds=cumulative,
            chars_used=chapter_chars,
        )
