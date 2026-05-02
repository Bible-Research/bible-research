"""Generate Cloud TTS audio + timestamps for missing chapters and upload
them to GCS. Designed to be invoked by a Cloud Run Job once per month."""
import json
import logging
import sys
from pathlib import Path

from django.core.management.base import BaseCommand

from bible.services.google_tts.client import QuotaExceeded
from bible.services.google_tts.synthesizer import Synthesizer
from bible.services.storage import gcs
from bible.services.sword.registry import canonical_sword_fileset_id
from bible.utils.bible_books import _BIBLE_BOOKS

logger = logging.getLogger(__name__)

CANONICAL_VERSES_JSON = (
    Path(__file__).resolve().parents[2] / "esv_bible_verses.json"
)


def _load_canonical_worklist():
    """Return ordered ``[(book_id, chapter), ...]`` for the whole Bible
    using bible/esv_bible_verses.json as the canonical chapter source."""
    raw = json.loads(CANONICAL_VERSES_JSON.read_text())
    name_to_id = {name.lower(): code for name, code, _ in _BIBLE_BOOKS}
    book_order = [code for _, code, _ in _BIBLE_BOOKS]
    by_book: dict[str, list[int]] = {}
    for book_name, payload in raw.items():
        book_id = name_to_id.get(book_name.lower())
        if not book_id:
            continue
        chapters = sorted(int(c) for c in payload["chapters"].keys())
        by_book[book_id] = chapters
    out: list[tuple[str, int]] = []
    for book_id in book_order:
        for chap in by_book.get(book_id, []):
            out.append((book_id, chap))
    return out


class Command(BaseCommand):
    help = "Generate missing chapter audio + timestamps via Cloud TTS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fileset-id", default="LVSGLU8",
            help="Canonical SWORD fileset id (default: LVSGLU8).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="List what would be generated; do not call TTS or write GCS.",
        )

    def handle(self, *args, **options):
        fileset_id = canonical_sword_fileset_id(options["fileset_id"])
        if not fileset_id:
            self.stderr.write(
                f"Unknown fileset_id: {options['fileset_id']!r}"
            )
            sys.exit(2)
        dry_run = options["dry_run"]

        worklist = _load_canonical_worklist()
        completed = (
            set() if dry_run else gcs.list_completed_chapters(fileset_id)
        )
        pending = [bc for bc in worklist if bc not in completed]

        logger.info(
            "fileset=%s total=%d completed=%d pending=%d",
            fileset_id, len(worklist), len(completed), len(pending),
        )
        if dry_run:
            for book_id, chap in pending[:20]:
                self.stdout.write(f"would generate {book_id} {chap}")
            self.stdout.write(
                f"... ({len(pending)} pending; dry-run)"
            )
            return

        synthesizer = Synthesizer()
        generated = 0
        for book_id, chap in pending:
            try:
                artifacts = synthesizer.run(fileset_id, book_id, chap)
            except QuotaExceeded as exc:
                logger.warning(
                    "Cloud TTS quota exhausted at %s %s: %s. "
                    "Resuming next run.",
                    book_id, chap, exc,
                )
                self.stdout.write(
                    f"quota_exhausted next={book_id} {chap} "
                    f"generated={generated}"
                )
                return
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Failed to generate %s %s: %s",
                    book_id, chap, exc,
                )
                continue
            try:
                gcs.upload_chapter_artifacts(
                    fileset_id, book_id, chap,
                    artifacts.mp3_bytes,
                    artifacts.timestamps_payload,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Failed to upload %s %s: %s",
                    book_id, chap, exc,
                )
                continue
            generated += 1
            logger.info(
                "Generated %s %s duration=%.2fs",
                book_id, chap, artifacts.duration_seconds,
            )

        self.stdout.write(
            f"done generated={generated} pending_after={len(pending) - generated}"
        )
