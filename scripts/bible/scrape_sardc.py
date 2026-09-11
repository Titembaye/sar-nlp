"""Collecte la Bible SARDC (sar) depuis bible.com par scraping navigateur.

La Bible SARDC (Alliance Biblique du Tchad, 2006/2010) n'est pas disponible en
téléchargement direct ; ce script pilote un navigateur headless (Playwright) pour
visiter chaque chapitre de bible.com/fr/bible/445 (version SARDC) et en extraire
les versets, d'abord par une regex sur le HTML rendu, avec un repli JS
(`page.evaluate`) si la regex ne trouve rien (mise en page différente selon les
livres). Un verset est repéré par son attribut `data-usfm` (ex. `GEN.1.1`).

Reprise sur interruption : les couples (livre, chapitre) déjà présents dans le
fichier de sortie sont relus au démarrage et sautés (`load_existing_verses` +
`done_refs`), donc on peut relancer le script après une coupure sans dupliquer
ni perdre de progrès.

Respect du serveur : `DELAY` secondes entre deux requêtes.

⚠️ Licence : ce corpus est © Alliance Biblique du Tchad — ne pas redistribuer
sans autorisation (voir data/README.md). Ce script sert à la collecte pour usage
de recherche, pas à la republication du texte biblique.

Usage :
    pip install playwright && playwright install chromium
    python -m scripts.bible.scrape_sardc
"""
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


def load_existing_verses() -> list[dict]:
    """Relit les versets déjà scrapés dans `OUTPUT_JSONL`, s'il existe.

    Nécessaire pour la reprise : `main` écrase `OUTPUT_JSONL` à chaque exécution
    (voir sa docstring), donc il faut recharger l'existant ici puis le combiner
    aux nouveaux versets avant de réécrire, sous peine de perdre les chapitres
    déjà collectés lors d'une exécution précédente.
    """
    verses = []
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, encoding='utf-8') as f:
            for line in f:
                try:
                    verses.append(json.loads(line))
                except Exception:
                    pass
    return verses


def done_refs(existing_verses: list[dict]) -> set[tuple[str, int]]:
    """Ensemble des chapitres (livre, numéro) déjà présents parmi `existing_verses`,
    pour sauter ces chapitres au lieu de les re-scraper."""
    return {(v['book'], v['chapter']) for v in existing_verses}


def extract_verses(page_handle, book, chapter):
    """Extrait les versets d'un chapitre déjà chargé dans `page_handle`.

    Essaie d'abord une regex sur le HTML rendu (rapide) ; si elle ne trouve
    aucun verset (mise en page différente), retombe sur une extraction en JS
    via `data-usfm`, plus lente mais plus robuste.
    """
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
    """Parcourt tous les livres/chapitres de `BOOKS`, saute ceux déjà scrapés,
    et réécrit `OUTPUT_JSONL` avec l'ensemble (anciens + nouveaux versets).

    Reprenable : si le script est interrompu, les chapitres déjà écrits lors
    d'une exécution précédente sont rechargés (`load_existing_verses`) puis
    sautés (`done_refs`) plutôt que re-scrapés, et réécrits tels quels avec les
    nouveaux à la fin — aucune perte de progrès d'une exécution à l'autre.
    """
    if sync_playwright is None:
        raise RuntimeError("Playwright is not installed. Install with: pip install playwright")

    print("Scraping SARDC Bible corpus...")
    existing_verses = load_existing_verses()
    done = done_refs(existing_verses)
    all_verses = list(existing_verses)  # on repart de l'existant, pas d'une liste vide

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

    new_count = len(all_verses) - len(existing_verses)
    print(f"\n{new_count} new verses ({len(all_verses)} total) -> {OUTPUT_JSONL}")


if __name__ == '__main__':
    main()
