"""Registry of locally-bundled SWORD Bible modules served via pysword."""
from pathlib import Path

# Directory holding the vendored CrossWire raw-zip modules.
SWORD_MODULES_DIR = Path(__file__).resolve().parents[2] / "sword_modules"

# Map of synthetic fileset_id -> module metadata.
# fileset_id convention: 3-letter ISO 639-3 language code + short abbr,
# matching the DBT id style (e.g. ENGESV) so existing clients don't need
# to special-case routing.
SWORD_TRANSLATIONS = {
    "LVSGLU8": {
        "module_name": "LvGluck8",
        "zip_filename": "LvGluck8.zip",
        "name": "Latvian Glück 8th edition",
        "abbr": "GLU8",
        "language": "Latvian",
        "language_iso": "lvs",  # ISO 639-3
        "license": "Public Domain",
    },
}


def canonical_sword_fileset_id(fileset_id: str) -> str | None:
    """Return the registry key (e.g. LVSGLU8) for a fileset id or abbr (e.g. GLU8)."""
    if not fileset_id:
        return None
    key = fileset_id.strip().upper()
    if key in SWORD_TRANSLATIONS:
        return key
    for sfid, meta in SWORD_TRANSLATIONS.items():
        if meta["abbr"].upper() == key:
            return sfid
    return None


def is_sword_fileset(fileset_id: str) -> bool:
    return canonical_sword_fileset_id(fileset_id) is not None


def get_sword_meta(fileset_id: str) -> dict:
    canon = canonical_sword_fileset_id(fileset_id)
    if canon is None:
        raise KeyError(fileset_id)
    return SWORD_TRANSLATIONS[canon]
