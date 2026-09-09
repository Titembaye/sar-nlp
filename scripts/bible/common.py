"""
Shared utilities for Sar-French Bible alignment.

French Bible sources (choose one, download to data/raw/):
  - OPUS Bible-uedin (auto-downloaded by fetch_french_bible.py)
  - eBible.org: download French Louis Segond 1910 plain text
    Save as: data/raw/french_bible_lsg.txt
    Format:  GEN 1:1 Au commencement, Dieu créa les cieux et la terre.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

SARDC_PATH = Path("data/raw/bible/sardc_corpus.jsonl")
FRENCH_BIBLE_PATH = Path("data/raw/bible/french_bible_lsg.jsonl")
PAIRS_OUTPUT_PATH = Path("data/processed/bible/sar_fr_bible_pairs.csv")

# Standard Protestant Bible book order (1-66) → USFM codes
BOOK_NUM_TO_USFM: dict[int, str] = {
    1: 'GEN', 2: 'EXO', 3: 'LEV', 4: 'NUM', 5: 'DEU',
    6: 'JOS', 7: 'JDG', 8: 'RUT', 9: '1SA', 10: '2SA',
    11: '1KI', 12: '2KI', 13: '1CH', 14: '2CH', 15: 'EZR',
    16: 'NEH', 17: 'EST', 18: 'JOB', 19: 'PSA', 20: 'PRO',
    21: 'ECC', 22: 'SNG', 23: 'ISA', 24: 'JER', 25: 'LAM',
    26: 'EZK', 27: 'DAN', 28: 'HOS', 29: 'JOL', 30: 'AMO',
    31: 'OBA', 32: 'JON', 33: 'MIC', 34: 'NAM', 35: 'HAB',
    36: 'ZEP', 37: 'HAG', 38: 'ZEC', 39: 'MAL',
    40: 'MAT', 41: 'MRK', 42: 'LUK', 43: 'JHN', 44: 'ACT',
    45: 'ROM', 46: '1CO', 47: '2CO', 48: 'GAL', 49: 'EPH',
    50: 'PHP', 51: 'COL', 52: '1TH', 53: '2TH', 54: '1TI',
    55: '2TI', 56: 'TIT', 57: 'PHM', 58: 'HEB', 59: 'JAS',
    60: '1PE', 61: '2PE', 62: '1JN', 63: '2JN', 64: '3JN',
    65: 'JUD', 66: 'REV',
}

# Reverse: USFM → canonical order index (for sorting)
BOOK_ORDER: dict[str, int] = {usfm: num for num, usfm in BOOK_NUM_TO_USFM.items()}

# OSIS IDs used in some XML corpora → USFM
OSIS_TO_USFM: dict[str, str] = {
    'Gen': 'GEN', 'Exod': 'EXO', 'Lev': 'LEV', 'Num': 'NUM', 'Deut': 'DEU',
    'Josh': 'JOS', 'Judg': 'JDG', 'Ruth': 'RUT', '1Sam': '1SA', '2Sam': '2SA',
    '1Kgs': '1KI', '2Kgs': '2KI', '1Chr': '1CH', '2Chr': '2CH', 'Ezra': 'EZR',
    'Neh': 'NEH', 'Esth': 'EST', 'Job': 'JOB', 'Ps': 'PSA', 'Prov': 'PRO',
    'Eccl': 'ECC', 'Song': 'SNG', 'Isa': 'ISA', 'Jer': 'JER', 'Lam': 'LAM',
    'Ezek': 'EZK', 'Dan': 'DAN', 'Hos': 'HOS', 'Joel': 'JOL', 'Amos': 'AMO',
    'Obad': 'OBA', 'Jonah': 'JON', 'Mic': 'MIC', 'Nah': 'NAM', 'Hab': 'HAB',
    'Zeph': 'ZEP', 'Hag': 'HAG', 'Zech': 'ZEC', 'Mal': 'MAL',
    'Matt': 'MAT', 'Mark': 'MRK', 'Luke': 'LUK', 'John': 'JHN', 'Acts': 'ACT',
    'Rom': 'ROM', '1Cor': '1CO', '2Cor': '2CO', 'Gal': 'GAL', 'Eph': 'EPH',
    'Phil': 'PHP', 'Col': 'COL', '1Thess': '1TH', '2Thess': '2TH',
    '1Tim': '1TI', '2Tim': '2TI', 'Titus': 'TIT', 'Phlm': 'PHM',
    'Heb': 'HEB', 'Jas': 'JAS', '1Pet': '1PE', '2Pet': '2PE',
    '1John': '1JN', '2John': '2JN', '3John': '3JN', 'Jude': 'JUD', 'Rev': 'REV',
}

# eBible plain-text: "GEN 1:1 text..."
_EBIBLE_LINE = re.compile(r'^([1-3]?[A-Z]+)\s+(\d+):(\d+)\s+(.+)$')


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

_IOTA_STROKE = 'ᵼ'  # ᵼ — PDF encoding artifact that should be ə (U+0259)


_STUB_RE = re.compile(r'^\d+(\.\d+)*$')  # "1", "13.5", "1.2.3" etc.


def _is_stub(text: str) -> bool:
    """Return True if text is a verse reference stub, not real Sar content."""
    return bool(_STUB_RE.match(text.strip()))


def _fix_sar_text(text: str) -> str:
    return text.replace(_IOTA_STROKE, 'ə')


def load_sardc(path: Path = SARDC_PATH) -> dict[str, str]:
    """
    Load SARDC corpus as {ref: text}.

    The corpus has multiple entries per ref: a numeric stub (verse number)
    followed by the actual Sar text (sometimes split across lines).
    We skip stubs and concatenate all real-text fragments per ref.
    """
    fragments: dict[str, list[str]] = defaultdict(list)
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            text = entry['text'].strip()
            if not _is_stub(text) and text:
                fragments[entry['ref']].append(_fix_sar_text(text))

    return {ref: ' '.join(parts) for ref, parts in fragments.items()}


def load_french_bible_jsonl(path: Path) -> dict[str, str]:
    """Load French Bible from JSONL. Returns {ref: text}."""
    verses: dict[str, str] = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            ref = entry['ref']
            if ref not in verses:
                verses[ref] = entry['text']
    return verses


def load_french_bible_ebible(path: Path) -> dict[str, str]:
    """Load eBible plain-text format: 'GEN 1:1 text...'"""
    verses: dict[str, str] = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = _EBIBLE_LINE.match(line)
            if m:
                book, ch, verse, text = m.groups()
                ref = f"{book}.{ch}.{verse}"
                if ref not in verses:
                    verses[ref] = text.strip()
    return verses


def load_french_bible(path: Path) -> dict[str, str]:
    """Auto-detect format (JSONL or eBible plain text) and load."""
    with open(path, encoding='utf-8') as f:
        first = f.readline().strip()
    if first.startswith('{'):
        return load_french_bible_jsonl(path)
    return load_french_bible_ebible(path)


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def _sardc_book_index(
    sar_verses: dict[str, str],
) -> dict[str, list[tuple[int, int, str, str]]]:
    """Build per-book sorted list of (chapter, verse, ref, text) from SARDC."""
    by_book: dict[str, list] = defaultdict(list)
    for ref, text in sar_verses.items():
        parts = ref.split('.')
        if len(parts) != 3:
            continue
        book, ch, verse = parts
        try:
            by_book[book].append((int(ch), int(verse), ref, text))
        except ValueError:
            pass
    for book in by_book:
        by_book[book].sort()
    return dict(by_book)


def _fr_book_index(
    fr_verses: dict[str, str],
) -> dict[str, list[tuple[int, str]]]:
    """Build per-book sorted list of (absVerse, text) from OPUS-format French Bible."""
    by_book: dict[str, list] = defaultdict(list)
    for ref, text in fr_verses.items():
        parts = ref.split('.')
        if len(parts) != 2:
            continue
        book, abs_verse = parts
        try:
            by_book[book].append((int(abs_verse), text))
        except ValueError:
            pass
    for book in by_book:
        by_book[book].sort()
    return dict(by_book)


def _is_opus_format(fr_verses: dict[str, str]) -> bool:
    """Return True if refs are OPUS 2-part format (BOOK.ABSVERSE)."""
    if not fr_verses:
        return False
    sample = next(iter(fr_verses))
    return len(sample.split('.')) == 2


def align_verses(
    sar_verses: dict[str, str],
    fr_verses: dict[str, str],
) -> list[dict]:
    """
    Align Sar and French Bible verses.
    - If French refs are 3-part (BOOK.CH.V): exact ref matching.
    - If French refs are 2-part (BOOK.ABSVERSE, from OPUS): positional matching per book.
    """
    if _is_opus_format(fr_verses):
        return _align_positional(sar_verses, fr_verses)
    return _align_exact(sar_verses, fr_verses)


def _align_exact(sar_verses: dict[str, str], fr_verses: dict[str, str]) -> list[dict]:
    common_refs = sorted(set(sar_verses) & set(fr_verses))
    return [
        {'ref': ref, 'sar': sar_verses[ref], 'fr': fr_verses[ref]}
        for ref in common_refs
    ]


def _align_positional(
    sar_verses: dict[str, str],
    fr_verses: dict[str, str],
) -> list[dict]:
    """
    Align by position within each book.
    OPUS uses absolute verse numbers within a book (no chapter separator), so
    we match: Sar verse N in book X ↔ French verse N in book X.
    ~1.5% alignment error due to ~478 missing verses in SARDC vs standard Bible.
    """
    sar_by_book = _sardc_book_index(sar_verses)
    fr_by_book = _fr_book_index(fr_verses)

    common_books = sorted(
        set(sar_by_book) & set(fr_by_book),
        key=lambda b: BOOK_ORDER.get(b, 999),
    )

    pairs = []
    for book in common_books:
        sar_list = sar_by_book[book]
        fr_list = fr_by_book[book]
        for (ch, verse, ref, sar_text), (_, fr_text) in zip(sar_list, fr_list):
            pairs.append({'ref': ref, 'sar': sar_text, 'fr': fr_text})

    return pairs


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_pairs_csv(path: Path, pairs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ref', 'sar', 'fr'])
        writer.writeheader()
        writer.writerows(pairs)


def write_pairs_jsonl(path: Path, pairs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
