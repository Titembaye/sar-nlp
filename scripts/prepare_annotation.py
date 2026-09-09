"""
Prépare les fichiers CSV prêts à importer dans DATA4CHAD.

Produit 4 fichiers dans data/annotation_ready/ :
  sentences_fr_sar.csv   — phrases françaises à traduire en Sar
  sentences_sar_fr.csv   — phrases Sar à traduire en français
  words_fr_sar.csv       — mots français extraits des phrases (avec contexte)
  words_sar_fr.csv       — mots Sar extraits des phrases (avec contexte)

Sources phrases françaises :
  - Côté FR des paires bilingues (bible, dictionary, sara_lexicon)
  - data/processed/tatoeba/fra_filtered.jsonl

Sources phrases Sar :
  - Côté Sar des paires bilingues

Colonnes :
  text, source_language, target_language, granularity, context, source

Usage :
  python -m scripts.prepare_annotation
  python -m scripts.prepare_annotation --max-sentences 5000 --min-words 3
"""

import re
import csv
import json
import argparse
from pathlib import Path
from collections import OrderedDict

ROOT           = Path(__file__).parent.parent
DATA_PROCESSED = ROOT / 'data' / 'processed'
OUTPUT_DIR     = ROOT / 'data' / 'annotation_ready'

ALL_PAIRS_PATH = DATA_PROCESSED / 'sar_fr_all_pairs.jsonl'
TATOEBA_PATH   = DATA_PROCESSED / 'tatoeba' / 'fra_filtered.jsonl'

FR_STOPWORDS = {
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
    'et', 'ou', 'ni', 'mais', 'donc', 'or', 'car', 'que', 'qui',
    'il', 'elle', 'ils', 'elles', 'je', 'tu', 'nous', 'vous', 'on',
    'me', 'te', 'se', 'lui', 'leur', 'y', 'en',
    'ce', 'cet', 'cette', 'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa',
    'notre', 'votre', 'leur', 'mes', 'tes', 'ses', 'nos', 'vos', 'leurs',
    'à', 'par', 'pour', 'sur', 'sous', 'dans', 'avec', 'sans', 'entre',
    'vers', 'chez', 'dont', 'où', 'quand', 'comment', 'si', 'ne', 'pas',
    'plus', 'très', 'bien', 'tout', 'tous', 'toute', 'toutes', 'aussi',
    'est', 'sont', 'était', 'ont', 'avait', 'être', 'avoir', 'faire',
    'dit', 'va', 'été',
}

SAR_STOPWORDS = {
    'ā', 'à', 'a', 'ń', 'nī', 'tə́', 'kə', 'ní', 'gə̄', 'ō',
}


def tokenize_fr(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-ZÀ-ÿ]+(?:[-'][a-zA-ZÀ-ÿ]+)*", text)
    seen, result = set(), []
    for w in raw:
        low = w.lower()
        if len(low) >= 3 and low not in FR_STOPWORDS and low not in seen:
            seen.add(low)
            result.append(w)
    return result


def tokenize_sar(text: str) -> list[str]:
    raw = re.findall(
        r"[a-zA-ZÀ-ÿĀ-ɏḀ-ỿ̀-ͯḀ-ỿɐ-ʯ]+"
        r"(?:[-'][a-zA-ZÀ-ÿĀ-ɏ̀-ͯ]+)*",
        text,
        flags=re.UNICODE,
    )
    seen, result = set(), []
    for w in raw:
        low = w.lower()
        if len(low) >= 2 and low not in SAR_STOPWORDS and low not in seen:
            seen.add(low)
            result.append(w)
    return result


def load_pairs() -> list[dict]:
    pairs = []
    with open(ALL_PAIRS_PATH, encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            sar = obj.get('sar', '').strip()
            fr  = obj.get('fr', '').strip()
            if sar and fr:
                pairs.append({'sar': sar, 'fr': fr, 'source': obj.get('source', 'unknown')})
    return pairs


def load_tatoeba() -> list[str]:
    sentences = []
    if not TATOEBA_PATH.exists():
        print("  Tatoeba non disponible, ignoré.")
        return sentences
    with open(TATOEBA_PATH, encoding='utf-8') as f:
        for line in f:
            text = json.loads(line).get('text', '').strip()
            if text:
                sentences.append(text)
    return sentences


def deduplicate(rows: list[dict], key: str) -> list[dict]:
    seen, result = set(), []
    for row in rows:
        norm = row[key].strip().lower()
        if norm not in seen:
            seen.add(norm)
            result.append(row)
    return result


def build_sentences(pairs: list[dict], tatoeba: list[str],
                    max_rows: int, min_words: int) -> tuple[list, list]:
    fr_rows, sar_rows = [], []

    for p in pairs:
        if len(p['fr'].split()) >= min_words:
            fr_rows.append({
                'text': p['fr'], 'source_language': 'french',
                'target_language': 'saar', 'granularity': 'sentence',
                'context': '', 'source': p['source'],
            })
        if len(p['sar'].split()) >= min_words:
            sar_rows.append({
                'text': p['sar'], 'source_language': 'saar',
                'target_language': 'french', 'granularity': 'sentence',
                'context': '', 'source': p['source'],
            })

    for text in tatoeba:
        if len(text.split()) >= min_words:
            fr_rows.append({
                'text': text, 'source_language': 'french',
                'target_language': 'saar', 'granularity': 'sentence',
                'context': '', 'source': 'tatoeba',
            })

    fr_rows  = deduplicate(fr_rows, 'text')
    sar_rows = deduplicate(sar_rows, 'text')

    if max_rows:
        fr_rows  = fr_rows[:max_rows]
        sar_rows = sar_rows[:max_rows]

    return fr_rows, sar_rows


def build_words(pairs: list[dict], max_rows: int) -> tuple[list, list]:
    fr_words:  dict[str, dict] = OrderedDict()
    sar_words: dict[str, dict] = OrderedDict()

    for p in pairs:
        for w in tokenize_fr(p['fr']):
            key = w.lower()
            if key not in fr_words:
                fr_words[key] = {
                    'text': w, 'source_language': 'french',
                    'target_language': 'saar', 'granularity': 'word',
                    'context': p['fr'], 'source': p['source'],
                }
        for w in tokenize_sar(p['sar']):
            key = w.lower()
            if key not in sar_words:
                sar_words[key] = {
                    'text': w, 'source_language': 'saar',
                    'target_language': 'french', 'granularity': 'word',
                    'context': p['sar'], 'source': p['source'],
                }

    fr_rows  = list(fr_words.values())
    sar_rows = list(sar_words.values())

    if max_rows:
        fr_rows  = fr_rows[:max_rows]
        sar_rows = sar_rows[:max_rows]

    return fr_rows, sar_rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ['text', 'source_language', 'target_language', 'granularity', 'context', 'source']
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name:<35} {len(rows):>7,} lignes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-sentences', type=int, default=0,
                        help='Nombre max de phrases par fichier (0 = illimité)')
    parser.add_argument('--max-words', type=int, default=0,
                        help='Nombre max de mots par fichier (0 = illimité)')
    parser.add_argument('--min-words', type=int, default=2,
                        help='Nombre min de mots par phrase (défaut: 2)')
    args = parser.parse_args()

    print("Chargement des paires bilingues...")
    pairs = load_pairs()
    print(f"  {len(pairs):,} paires chargées")

    print("Chargement Tatoeba...")
    tatoeba = load_tatoeba()
    print(f"  {len(tatoeba):,} phrases Tatoeba chargées")

    print("\nGénération des phrases...")
    fr_sent, sar_sent = build_sentences(pairs, tatoeba, args.max_sentences, args.min_words)
    write_csv(fr_sent,  OUTPUT_DIR / 'sentences_fr_sar.csv')
    write_csv(sar_sent, OUTPUT_DIR / 'sentences_sar_fr.csv')

    print("\nGénération des mots...")
    fr_words, sar_words = build_words(pairs, args.max_words)
    write_csv(fr_words,  OUTPUT_DIR / 'words_fr_sar.csv')
    write_csv(sar_words, OUTPUT_DIR / 'words_sar_fr.csv')

    total = len(fr_sent) + len(sar_sent) + len(fr_words) + len(sar_words)
    print(f"\nTotal : {total:,} entrées -> {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
