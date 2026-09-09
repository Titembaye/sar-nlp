import json
import re
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

BOOKS = {
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34,
    "JOS": 24, "JDG": 21, "RUT": 4,  "1SA": 31, "2SA": 24,
    "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36, "EZR": 10,
    "NEH": 13, "EST": 10, "JOB": 42, "PSA": 150, "PRO": 31,
    "ECC": 12, "SNG": 8,  "ISA": 66, "JER": 52, "LAM": 5,
    "EZK": 48, "DAN": 12, "HOS": 14, "JOL": 3,  "AMO": 9,
    "OBA": 1,  "JON": 4,  "MIC": 7,  "NAM": 3,  "HAB": 3,
    "ZEP": 3, "HAG": 2, "ZEC": 14, "MAL": 4,
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28,
    "ROM": 16, "1CO": 16, "2CO": 13, "GAL": 6,  "EPH": 6,
    "PHP": 4, "COL": 4, "1TH": 5,  "2TH": 3,  "1TI": 6,
    "2TI": 4, "TIT": 3, "PHM": 1, "HEB": 13, "JAS": 5,
    "1PE": 5, "2PE": 3, "1JN": 5,  "2JN": 1,  "3JN": 1,
    "JUD": 1, "REV": 22,
}

BASE_URL = "https://www.bible.com/fr/bible/445/{book}.{chapter}.SARDC"
DELAY = 1.0
OUTPUT_JSONL = Path("data/raw/bible/sardc_corpus.jsonl")


def load_done_refs() -> set[tuple[str, int]]:
    done = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, encoding='utf-8') as f:
            for line in f:
                try:
                    v = json.loads(line)
                    done.add((v['book'], v['chapter']))
                except Exception:
                    pass
    return done


def extract_verses(page_handle, book, chapter):
    try:
        page_handle.wait_for_selector("div[class*='chapter']", timeout=15000)
    except Exception:
        pass
    page_handle.wait_for_timeout(2000)
    html = page_handle.content()

    verses = []
    matches = re.findall(
        r'data-usfm="(' + re.escape(book) + r'\.' + str(chapter) + r'\.(\d+))"[^>]*>(.*?)</span>',
        html, re.DOTALL
    )

    for ref, verse_num, raw_html in matches:
        text = re.sub(r'<[^>]+>', ' ', raw_html)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            verses.append({
                'ref': ref,
                'book': book,
                'chapter': chapter,
                'verse': int(verse_num),
                'text': text,
            })

    if verses:
        return verses

    try:
        result = page_handle.evaluate("""() => {
            const verses = [];
            document.querySelectorAll('[data-usfm]').forEach(el => {
                const ref = el.getAttribute('data-usfm');
                const parts = ref.split('.');
                if (parts.length === 3) {
                    verses.push({
                        ref: ref,
                        book: parts[0],
                        chapter: parseInt(parts[1]),
                        verse: parseInt(parts[2]),
                        text: el.innerText
                    });
                }
            });
            return verses;
        }""")
        return result
    except Exception:
        return []


def main() -> None:
    if sync_playwright is None:
        raise RuntimeError("Playwright is not installed. Install with: pip install playwright")

    print("Scraping SARDC Bible corpus...")
    done = load_done_refs()
    all_verses = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for book_code, chapters in BOOKS.items():
            for chapter in range(1, chapters + 1):
                if (book_code, chapter) in done:
                    print(f"  skip {book_code} {chapter} (already scraped)")
                    continue

                url = BASE_URL.format(book=book_code, chapter=chapter)
                print(f"  -> {book_code} {chapter}...", end=" ", flush=True)

                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    verses = extract_verses(page, book_code, chapter)
                    all_verses.extend(verses)
                    print(f"OK ({len(verses)} verses)")
                    page.close()
                    time.sleep(DELAY)
                except Exception as e:
                    print(f"ERROR: {e}")
                    try:
                        page.close()
                    except Exception:
                        pass
                    time.sleep(DELAY)

        browser.close()

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for v in all_verses:
            f.write(json.dumps(v, ensure_ascii=False) + '\n')

    print(f"\n{len(all_verses)} verses scraped -> {OUTPUT_JSONL}")


if __name__ == '__main__':
    main()
