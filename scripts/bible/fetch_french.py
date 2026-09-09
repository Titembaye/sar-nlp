"""
Download French Louis Segond 1910 Bible and convert to JSONL.

Tries sources in order:
  1. OPUS Bible-uedin XML (verse IDs, NLP standard corpus)
  2. christos-c/bible-corpus GitHub XML
  3. eBible.org plain-text zip (several URL patterns)

Usage:
    python -m scripts.bible.fetch_french_bible

Output: data/raw/french_bible_lsg.jsonl
  - OPUS source  → 2-part refs: {"ref": "GEN.3",   "text": "..."}  (book.absVerse)
  - Other sources → 3-part refs: {"ref": "GEN.1.3", "text": "..."}  (book.ch.verse)
  align_parallel.py handles both formats automatically.

Manual fallback:
    Place a plain-text file at data/raw/french_bible_lsg.txt:
      GEN 1:1 Au commencement, Dieu créa les cieux et la terre.
    Then re-run — it will be converted automatically.
"""

import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import requests
except ImportError:
    requests = None  # type: ignore

OUTPUT_PATH = Path("data/raw/bible/french_bible_lsg.jsonl")
MANUAL_TXT_PATH = Path("data/raw/bible/french_bible_lsg.txt")

OPUS_XML_URL = "https://object.pouta.csc.fi/OPUS-bible-uedin/v1/xml/fr.zip"

GITHUB_XML_URLS = [
    "https://raw.githubusercontent.com/christos-c/bible-corpus/master/bibles/French.xml",
    "https://raw.githubusercontent.com/christos-c/bible-corpus/main/bibles/French.xml",
]

EBIBLE_URLS = [
    "https://ebible.org/Scriptures/frlsg_usfx.zip",
    "https://ebible.org/Scriptures/frlsg_readaloud.zip",
    "https://ebible.org/Scriptures/fraLSG.zip",
    "https://ebible.org/Scriptures/frlsg.zip",
]

# Numeric book order (1-66) → USFM codes (Protestant canon)
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

# OSIS book IDs (christos-c XML) → USFM
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

_EBIBLE_LINE = re.compile(r'^([1-3]?[A-Z]+)\s+(\d+):(\d+)\s+(.+)$')

# OPUS Bible-uedin uses non-standard book codes for 11 books.
# Map to SARDC / USFM standard codes so refs match after alignment.
OPUS_BOOK_REMAP: dict[str, str] = {
    'JOH': 'JHN',  # John
    'EZE': 'EZK',  # Ezekiel
    'JAM': 'JAS',  # James
    'JOE': 'JOL',  # Joel
    'MAR': 'MRK',  # Mark
    'SON': 'SNG',  # Song of Songs
    'PHI': 'PHP',  # Philippians
    '1JO': '1JN',  # 1 John
    '2JO': '2JN',  # 2 John
    '3JO': '3JN',  # 3 John
    'NAH': 'NAM',  # Nahum
}


def _get(url: str, timeout: int = 60) -> bytes:
    if requests is None:
        raise RuntimeError("pip install requests")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Text cleaner
# ---------------------------------------------------------------------------

_INLINE_VERSENUM = re.compile(r'\(\s*\d+\s*:\s*\d+\s*\)\s*')
_SELAH_RE = re.compile(r'\s*[-–]\s*(Pause|S[eé]la)\.?\s*$', re.IGNORECASE)


def _clean_opus_text(text: str) -> str:
    """Remove OPUS word-level tokenization artifacts and inline verse-number markers."""
    text = re.sub(r'\s+', ' ', text)                    # collapse whitespace/newlines
    text = re.sub(r' ([.,;:!?)\]»])', r'\1', text)     # space before punctuation
    text = re.sub(r'([(\[«]) ', r'\1', text)            # space after opening bracket
    text = re.sub(r'\s*`\s*', "'", text)                # backtick apostrophes
    # OPUS embeds inline (ch:v) markers for versification bookkeeping — remove from content
    text = _INLINE_VERSENUM.sub('', text)
    text = _SELAH_RE.sub('', text)                      # strip Selah / Pause liturgical markers
    return text.strip()


def _leading_inline_verse(raw_text: str) -> int | None:
    """
    If the raw (pre-clean) OPUS verse text starts with '(ch:v)', return v.
    Used to remap OPUS verse numbers to the original Hebrew verse numbers,
    because OPUS sometimes merges title verses, shifting all subsequent verse
    numbers by 1 (most common in Psalms, also Job, Hosea, Ezekiel, etc.).
    """
    m = re.match(r'^\s*\(\s*(\d+)\s*:\s*(\d+)\s*\)', raw_text)
    return int(m.group(2)) if m else None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_opus_xml_zip(raw: bytes) -> list[dict]:
    """
    Parse OPUS Bible-uedin XML zip.

    Segment ID format: '{prefix}.{USFM_BOOK}.{chapter}.{verse}.{subSentence}'
    Example: 'b.GEN.1.3.2' = Genesis ch1, verse 3, sentence 2

    Strategy:
      1. Parse USFM book code directly from the segment ID
      2. Group sub-sentences by (book, ch, verse), merge in order
      3. Output 3-part refs 'GEN.1.3' matching SARDC format → exact alignment
    """
    # Matches: any_prefix.BOOK.chapter.verse  OR  any_prefix.BOOK.chapter.verse.sub
    _SEG_RE = re.compile(
        r'^[^.]+\.([A-Z0-9]+)\.(\d+)\.(\d+)(?:\.(\d+))?$'
    )

    raw_segs: dict[tuple, list] = defaultdict(list)

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith('.xml')]
        if not xml_files:
            raise ValueError(f"No XML in zip. Contents: {zf.namelist()}")
        content = zf.read(xml_files[0])

    root = ET.fromstring(content)
    for s in root.iter('s'):
        sid = s.get('id', '')
        m = _SEG_RE.match(sid)
        if not m:
            continue
        book = OPUS_BOOK_REMAP.get(m.group(1), m.group(1))
        ch = int(m.group(2))
        verse = int(m.group(3))
        sub = int(m.group(4)) if m.group(4) else 1

        raw_text = ''.join(s.itertext())
        raw_segs[(book, ch, verse)].append((sub, raw_text))

    entries = []
    for (book, ch, verse), sub_list in sorted(raw_segs.items()):
        sub_list.sort()
        raw_merged = ' '.join(t for _, t in sub_list)

        # Remap verse number: if raw text starts with '(ch:v)', use v as the
        # canonical (Hebrew) verse number. OPUS shifts numbering in books where
        # the title/superscription is counted as verse 1 (Psalms, Job, etc.).
        inline_v = _leading_inline_verse(raw_merged)
        real_verse = inline_v if inline_v is not None else verse

        cleaned = _clean_opus_text(raw_merged)
        if cleaned:
            entries.append({'ref': f'{book}.{ch}.{real_verse}', 'text': cleaned})

    # After remapping, deduplicate refs: keep last entry per ref
    # (rare case: two OPUS entries remap to same Hebrew verse)
    seen: dict[str, dict] = {}
    for e in entries:
        seen[e['ref']] = e
    _book_order = {v: k for k, v in BOOK_NUM_TO_USFM.items()}
    return sorted(seen.values(), key=lambda e: (
        _book_order.get(e['ref'].split('.')[0], 999),
        int(e['ref'].split('.')[1]),
        int(e['ref'].split('.')[2]),
    ))


def _parse_github_xml(content: bytes) -> list[dict]:
    """Parse christos-c/bible-corpus XML. osisID format: 'Gen.1.1'"""
    entries = []
    root = ET.fromstring(content)
    ns = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
    verses = root.findall('.//osis:verse', ns) or root.findall('.//verse')
    for v in verses:
        osis_id = v.get('osisID', '')
        if not osis_id:
            continue
        parts = osis_id.split('.')
        if len(parts) != 3:
            continue
        book_osis, ch, verse = parts
        book = OSIS_TO_USFM.get(book_osis, book_osis.upper())
        text = (v.text or '').strip()
        if text:
            entries.append({'ref': f'{book}.{ch}.{verse}', 'text': text})
    return entries


def _parse_ebible_text(text: str) -> list[dict]:
    """Parse eBible plain-text: one verse per line 'GEN 1:1 text...'"""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = _EBIBLE_LINE.match(line)
        if m:
            book, ch, verse, content = m.groups()
            entries.append({'ref': f'{book}.{ch}.{verse}', 'text': content.strip()})
    return entries


def _parse_ebible_zip(raw: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        txts = [n for n in zf.namelist() if n.endswith('.txt')]
        if not txts:
            raise ValueError(f"No .txt in zip. Contents: {zf.namelist()}")
        main_txt = next(
            (n for n in txts if not any(k in n.lower() for k in ('about', 'copy', 'readme', 'license'))),
            txts[0],
        )
        content = zf.read(main_txt).decode('utf-8', errors='replace')
    return _parse_ebible_text(content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')


def main(output_path: Path = OUTPUT_PATH) -> Path:
    if output_path.exists():
        count = sum(1 for _ in open(output_path, encoding='utf-8'))
        print(f"Already exists: {output_path} ({count:,} verses). Delete to re-download.")
        return output_path

    if MANUAL_TXT_PATH.exists():
        print(f"Manual file found: {MANUAL_TXT_PATH}")
        entries = _parse_ebible_text(MANUAL_TXT_PATH.read_text(encoding='utf-8'))
        if entries:
            _write_jsonl(output_path, entries)
            print(f"  {len(entries):,} verses -> {output_path}")
            return output_path

    entries: list[dict] = []

    print(f"Trying OPUS Bible-uedin XML ...")
    try:
        data = _get(OPUS_XML_URL, timeout=120)
        entries = _parse_opus_xml_zip(data)
        if entries:
            print(f"  Parsed {len(entries):,} verse groups from OPUS XML")
    except Exception as e:
        print(f"  Failed: {e}")

    if not entries:
        for url in GITHUB_XML_URLS:
            print(f"Trying GitHub XML: {url} ...")
            try:
                data = _get(url)
                entries = _parse_github_xml(data)
                if entries:
                    print(f"  Parsed {len(entries):,} verses")
                    break
            except Exception as e:
                print(f"  Failed: {e}")

    if not entries:
        for url in EBIBLE_URLS:
            print(f"Trying {url} ...")
            try:
                data = _get(url)
                entries = _parse_ebible_zip(data)
                if entries:
                    print(f"  Parsed {len(entries):,} verses from zip")
                    break
            except Exception as e:
                print(f"  Failed: {e}")

    if not entries:
        raise RuntimeError(
            "All sources failed. Manual option:\n"
            "  1. Download Louis Segond plain text (one verse per line)\n"
            "  2. Save to data/raw/french_bible_lsg.txt\n"
            "     Format:  GEN 1:1 Au commencement...\n"
            "  3. Re-run this script"
        )

    _write_jsonl(output_path, entries)
    print(f"Saved: {len(entries):,} entries -> {output_path}")
    return output_path


if __name__ == '__main__':
    main()
