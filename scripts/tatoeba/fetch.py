"""
Télécharge et filtre les phrases françaises Tatoeba.

Source : https://downloads.tatoeba.org/exports/per_language/fra/fra_sentences.tsv.bz2
Format  : id<TAB>fra<TAB>texte (compressé bz2)

Filtres appliqués :
  - 3 à 15 mots
  - pas d'URL, pas de séquences numériques longues
  - longueur 10–250 caractères

Usage:
    python -m scripts.tatoeba.fetch
    python -m scripts.tatoeba.fetch --max 50000

Sorties :
  data/raw/tatoeba/fra_sentences.tsv.bz2     — fichier brut téléchargé
  data/processed/tatoeba/fra_filtered.jsonl  — phrases filtrées (champ: text, source)
"""

import argparse
import bz2
import json
import re
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

TATOEBA_URL = "https://downloads.tatoeba.org/exports/per_language/fra/fra_sentences.tsv.bz2"
RAW_PATH    = Path("data/raw/tatoeba/fra_sentences.tsv.bz2")
OUT_PATH    = Path("data/processed/tatoeba/fra_filtered.jsonl")

_URL_RE  = re.compile(r'https?://|www\.')
_LONG_NUM = re.compile(r'\d{5,}')


def _is_valid(text: str) -> bool:
    words = text.split()
    if not (3 <= len(words) <= 15):
        return False
    if len(text) < 10 or len(text) > 250:
        return False
    if _URL_RE.search(text):
        return False
    if _LONG_NUM.search(text):
        return False
    return True


def download() -> Path:
    if requests is None:
        raise RuntimeError("pip install requests")
    if RAW_PATH.exists():
        print(f"Déjà téléchargé : {RAW_PATH}")
        return RAW_PATH
    print(f"Téléchargement {TATOEBA_URL} ...")
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(TATOEBA_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(RAW_PATH, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    print(f"  -> {RAW_PATH}")
    return RAW_PATH


def filter_sentences(raw_path: Path, max_sentences: int = 0) -> list[str]:
    seen: set[str] = set()
    results = []
    with bz2.open(raw_path, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 3:
                continue
            text = parts[2].strip()
            low = text.lower()
            if low in seen or not _is_valid(text):
                continue
            seen.add(low)
            results.append(text)
            if max_sentences and len(results) >= max_sentences:
                break
    return results


def main(max_sentences: int = 0) -> Path:
    raw_path = download()

    print("Filtrage des phrases...")
    sentences = filter_sentences(raw_path, max_sentences)
    print(f"  {len(sentences):,} phrases conservées")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        for text in sentences:
            f.write(json.dumps({'text': text, 'source': 'tatoeba'}, ensure_ascii=False) + '\n')
    print(f"  -> {OUT_PATH}")
    return OUT_PATH


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=0,
                        help='Nombre max de phrases à garder (0 = toutes)')
    args = parser.parse_args()
    main(args.max)
