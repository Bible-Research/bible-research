"""Registry of ESV API-backed filesets."""
ESV_TRANSLATIONS = {
    "ENGESV_API": {
        "name": "English Standard Version",
        "abbr": "ESV",
        "language": "English",
        "language_iso": "eng",
        "license": "Copyright Crossway. See api.esv.org.",
    },
}


def canonical_esv_fileset_id(fileset_id: str) -> "str | None":
    if not fileset_id:
        return None
    key = fileset_id.strip().upper()
    return key if key in ESV_TRANSLATIONS else None


def is_esv_fileset(fileset_id: str) -> bool:
    return canonical_esv_fileset_id(fileset_id) is not None


def get_esv_translation_listing() -> list:
    """Return registry entries shaped like DBT/SWORD translations."""
    return [
        {
            "abbr": meta["abbr"],
            "name": meta["name"],
            "language": meta["language"],
            "iso": meta["language_iso"],
            "filesets": [
                {
                    "id": fid,
                    "type": "text_plain",
                    "size": "C",
                },
            ],
        }
        for fid, meta in ESV_TRANSLATIONS.items()
    ]
