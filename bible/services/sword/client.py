"""Thin pysword wrapper exposing the slice of the DBT client API used
by `BiblePassageSerializer`."""
import logging
import threading
from typing import Any, Dict, List

from pysword.modules import SwordModules

from bible.utils.bible_books import get_pysword_book_name

from .registry import (
    SWORD_MODULES_DIR,
    SWORD_TRANSLATIONS,
    canonical_sword_fileset_id,
    get_sword_meta,
)

logger = logging.getLogger(__name__)


class SwordClient:
    """Process-wide cache of pysword Bible objects loaded from vendored
    raw-zip modules. The `SwordModules` instance must be retained for
    the lifetime of the bible (it owns the open zip stream)."""

    def __init__(self):
        self._lock = threading.Lock()
        # fileset_id -> (SwordModules, SwordBible)
        self._cache: Dict[str, tuple] = {}

    def _load(self, fileset_id: str):
        canon = canonical_sword_fileset_id(fileset_id)
        if canon is None:
            raise ValueError(f"Unknown SWORD fileset_id: {fileset_id!r}")
        fileset_id = canon

        if fileset_id in self._cache:
            return self._cache[fileset_id]

        with self._lock:
            if fileset_id in self._cache:
                return self._cache[fileset_id]

            meta = get_sword_meta(fileset_id)
            zip_path = SWORD_MODULES_DIR / meta["zip_filename"]
            if not zip_path.exists():
                raise FileNotFoundError(
                    f"SWORD module zip not found: {zip_path}. "
                    f"Run scripts/download_sword_modules.sh."
                )

            modules = SwordModules(str(zip_path))
            modules.parse_modules()
            bible = modules.get_bible_from_module(meta["module_name"])
            self._cache[fileset_id] = (modules, bible)
            logger.info(
                "Loaded SWORD module %s (%s) for fileset_id=%s",
                meta["module_name"], meta["name"], fileset_id,
            )
            return self._cache[fileset_id]

    def get_chapter_verses(
        self, fileset_id: str, book_id: str, chapter: int
    ) -> List[Dict[str, Any]]:
        """Return [{verse_start, verse_text}, ...] for a chapter,
        matching the shape used by `BiblePassageSerializer`."""
        canon = canonical_sword_fileset_id(fileset_id)
        if canon is None:
            raise ValueError(f"Unknown SWORD fileset: {fileset_id!r}")
        _modules, bible = self._load(canon)

        pysword_book = get_pysword_book_name(book_id)
        if not pysword_book:
            raise ValueError(f"Unknown book id: {book_id}")

        verses: List[Dict[str, Any]] = []
        verse_num = 1
        while True:
            try:
                text = bible.get(
                    books=[pysword_book],
                    chapters=[int(chapter)],
                    verses=[verse_num],
                    clean=True,
                )
            except Exception:
                break
            text = (text or "").strip()
            if not text:
                break
            verses.append({"verse_start": verse_num, "verse_text": text})
            verse_num += 1
            if verse_num > 200:
                break

        if not verses:
            raise ValueError(
                f"No verses found for {book_id} {chapter} "
                f"in fileset_id={fileset_id}"
            )
        return verses

    def get_translation_listing(self) -> List[Dict[str, Any]]:
        """Return registry entries shaped like DBT translations."""
        out = []
        for fid, meta in SWORD_TRANSLATIONS.items():
            out.append({
                "abbr": meta["abbr"],
                "name": meta["name"],
                "language": meta["language"],
                "iso": meta["language_iso"],
                "filesets": [
                    {"id": fid, "type": "text_plain", "size": "C"},
                    {"id": fid, "type": "audio", "size": "C"},
                ],
            })
        return out


_default_client: "SwordClient | None" = None
_default_client_lock = threading.Lock()


def get_default_sword_client() -> "SwordClient":
    global _default_client
    if _default_client is None:
        with _default_client_lock:
            if _default_client is None:
                _default_client = SwordClient()
    return _default_client
