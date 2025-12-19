"""Utility functions for Bible books and standard abbreviations."""

# Book data: (book_name, book_code, testament)
# Testament: 'OT' = Old Testament, 'NT' = New Testament
_BIBLE_BOOKS = [
    # Old Testament
    ('genesis', 'GEN', 'OT'), ('exodus', 'EXO', 'OT'),
    ('leviticus', 'LEV', 'OT'), ('numbers', 'NUM', 'OT'),
    ('deuteronomy', 'DEU', 'OT'), ('joshua', 'JOS', 'OT'),
    ('judges', 'JDG', 'OT'), ('ruth', 'RUT', 'OT'),
    ('1 samuel', '1SA', 'OT'), ('2 samuel', '2SA', 'OT'),
    ('1 kings', '1KI', 'OT'), ('2 kings', '2KI', 'OT'),
    ('1 chronicles', '1CH', 'OT'), ('2 chronicles', '2CH', 'OT'),
    ('ezra', 'EZR', 'OT'), ('nehemiah', 'NEH', 'OT'),
    ('esther', 'EST', 'OT'), ('job', 'JOB', 'OT'),
    ('psalms', 'PSA', 'OT'), ('proverbs', 'PRO', 'OT'),
    ('ecclesiastes', 'ECC', 'OT'), ('song of solomon', 'SNG', 'OT'),
    ('isaiah', 'ISA', 'OT'), ('jeremiah', 'JER', 'OT'),
    ('lamentations', 'LAM', 'OT'), ('ezekiel', 'EZK', 'OT'),
    ('daniel', 'DAN', 'OT'), ('hosea', 'HOS', 'OT'),
    ('joel', 'JOL', 'OT'), ('amos', 'AMO', 'OT'),
    ('obadiah', 'OBA', 'OT'), ('jonah', 'JON', 'OT'),
    ('micah', 'MIC', 'OT'), ('nahum', 'NAM', 'OT'),
    ('habakkuk', 'HAB', 'OT'), ('zephaniah', 'ZEP', 'OT'),
    ('haggai', 'HAG', 'OT'), ('zechariah', 'ZEC', 'OT'),
    ('malachi', 'MAL', 'OT'),
    # New Testament
    ('matthew', 'MAT', 'NT'), ('mark', 'MRK', 'NT'),
    ('luke', 'LUK', 'NT'), ('john', 'JHN', 'NT'),
    ('acts of the apostles', 'ACT', 'NT'), ('romans', 'ROM', 'NT'),
    ('1 corinthians', '1CO', 'NT'), ('2 corinthians', '2CO', 'NT'),
    ('galatians', 'GAL', 'NT'), ('ephesians', 'EPH', 'NT'),
    ('philippians', 'PHP', 'NT'), ('colossians', 'COL', 'NT'),
    ('1 thessalonians', '1TH', 'NT'),
    ('2 thessalonians', '2TH', 'NT'),
    ('1 timothy', '1TI', 'NT'), ('2 timothy', '2TI', 'NT'),
    ('titus', 'TIT', 'NT'), ('philemon', 'PHM', 'NT'),
    ('hebrews', 'HEB', 'NT'), ('james', 'JAS', 'NT'),
    ('1 peter', '1PE', 'NT'), ('2 peter', '2PE', 'NT'),
    ('1 john', '1JN', 'NT'), ('2 john', '2JN', 'NT'),
    ('3 john', '3JN', 'NT'), ('jude', 'JUD', 'NT'),
    ('revelation', 'REV', 'NT'),
]

# Generate derived data structures from the single source
DBT_BOOK_NAME_TO_ID = {name: code for name, code, _ in _BIBLE_BOOKS}
BOOK_CODE_TO_TESTAMENT = {code: testament for _, code, testament in _BIBLE_BOOKS}
OLD_TESTAMENT_BOOKS = {code for _, code, t in _BIBLE_BOOKS if t == 'OT'}
NEW_TESTAMENT_BOOKS = {code for _, code, t in _BIBLE_BOOKS if t == 'NT'}


def get_dbt_book_id(book_name):
    """Convert a book name to its standard book ID.

    Args:
        book_name (str): The name of the book (e.g., '2 chronicles')

    Returns:
        str: The standard book ID (e.g., '2CH'), or None if not found
    """
    normalized = ' '.join(book_name.lower().strip().split())
    return DBT_BOOK_NAME_TO_ID.get(normalized, None)


def get_testament(book_id):
    """Determine which testament a book belongs to.

    Args:
        book_id (str): The DBT book ID (e.g., '2CH', 'MAT')

    Returns:
        str: 'OT' for Old Testament, 'NT' for New Testament,
             or None if book not found
    """
    return BOOK_CODE_TO_TESTAMENT.get(book_id.upper())


def get_audio_bible_id(
    book_id,
    base_translation='ENGESV',
    audio_type='1DA',
    codec='opus16'
):
    """Get the appropriate audio Bible ID based on testament.

    Args:
        book_id (str): The DBT book ID (e.g., '2CH', 'MAT')
        base_translation (str): Base translation code
                                (default: 'ENGESV')
        audio_type (str): Audio type code (default: '1DA')
        codec (str): Audio codec (default: 'opus16')

    Returns:
        str: The complete audio Bible ID
             (e.g., 'ENGESVO1DA-opus16' for OT books,
                  'ENGESVN1DA-opus16' for NT books)
    """
    testament = get_testament(book_id)
    if testament is None:
        # Default to OT if unknown
        testament = 'OT'

    # Convert testament to single letter for API
    # (API uses 'O' for Old Testament, 'N' for New Testament)
    testament_letter = testament[0]  # 'OT' -> 'O', 'NT' -> 'N'

    # Build the audio Bible ID
    audio_id = (
        f"{base_translation}{testament_letter}{audio_type}"
    )
    if codec:
        audio_id = f"{audio_id}-{codec}"

    return audio_id
