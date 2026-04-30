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


def is_sword_fileset(fileset_id: str) -> bool:
    return fileset_id in SWORD_TRANSLATIONS


def get_sword_meta(fileset_id: str) -> dict:
    return SWORD_TRANSLATIONS[fileset_id]
