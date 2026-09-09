"""
Construit le corpus Sar–Français final depuis toutes les sources traitées.

Sources parallèles (paires sar ↔ fr) :
  1. Bible alignée        — data/processed/bible/sar_fr_bible_pairs.jsonl
  2. Dictionnaire         — data/processed/dictionary/sar_dictionary_example_pairs.csv
  3. Lexique Sara         — data/processed/sara_lexicon/sar_fr_pairs.jsonl

Corpus monolingue Sar (pour pré-entraînement LM) :
  1. Bible SARDC          — data/raw/bible/sardc_corpus.jsonl
  2. Côté sar des paires ci-dessus
  3. Cosmogonie           — data/processed/cosmogonie/cosmogonie_sentences.jsonl

Sorties :
  data/processed/sar_fr_all_pairs.jsonl   — toutes les paires (sar, fr, source)
  data/processed/sar_fr_train.jsonl       — 90 %
  data/processed/sar_fr_val.jsonl         — 10 %
  data/processed/sar_monolingual.txt      — corpus monolingue Sar (1 phrase/ligne)

Usage:
    python -m scripts.build_corpus
"""

import csv
import json
import random
from pathlib import Path
from unicodedata import normalize

from scripts.bible.common import _fix_sar_text, _is_stub

BIBLE_PAIRS_PATH = Path("data/processed/bible/sar_fr_bible_pairs.jsonl")
DICT_PAIRS_PATH  = Path("data/processed/dictionary/sar_dictionary_example_pairs.csv")
LEXICON_PATH     = Path("data/processed/sara_lexicon/sar_fr_pairs.jsonl")
SARDC_RAW_PATH   = Path("data/raw/bible/sardc_corpus.jsonl")
COSMO_PATH       = Path("data/processed/cosmogonie/cosmogonie_sentences.jsonl")

ALL_PAIRS_PATH   = Path("data/processed/sar_fr_all_pairs.jsonl")
TRAIN_PATH       = Path("data/processed/sar_fr_train.jsonl")
VAL_PATH         = Path("data/processed/sar_fr_val.jsonl")
MONOLINGUAL_PATH = Path("data/processed/sar_monolingual.txt")

SEED = 42


def _clean(text: str) -> str:
    return normalize('NFC', text.strip())


def load_bible_pairs(path: Path) -> list[dict]:
    pairs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            e = json.loads(line.strip())
            sar, fr = _clean(e.get('sar', '')), _clean(e.get('fr', ''))
            if sar and fr:
                pairs.append({'sar': sar, 'fr': fr, 'source': 'bible'})
    return pairs


def load_dict_pairs(path: Path) -> list[dict]:
    pairs = []
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            sar, fr = _clean(row.get('sar', '')), _clean(row.get('fr', ''))
            if sar and fr:
                pairs.append({'sar': sar, 'fr': fr, 'source': 'dictionary'})
    return pairs


def load_lexicon_pairs(path: Path) -> list[dict]:
    pairs = []
    if not path.exists():
        return pairs
    with open(path, encoding='utf-8') as f:
        for line in f:
            e = json.loads(line.strip())
            fr  = _clean(e.get('source', ''))
            sar = _clean(e.get('target', ''))
            if sar and fr:
                pairs.append({'sar': sar, 'fr': fr, 'source': 'sara_lexicon'})
    return pairs


def load_sardc_sentences(path: Path) -> list[str]:
    sentences = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            text = e['text'].strip()
            if not _is_stub(text) and text:
                sentences.append(_clean(_fix_sar_text(text)))
    return sentences


def load_cosmo_sentences(path: Path) -> list[str]:
    sentences = []
    if not path.exists():
        return sentences
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            text = json.loads(line).get('text', '').strip()
            if text:
                sentences.append(_clean(text))
    return sentences


def main() -> None:
    print("=== Chargement des paires parallèles ===")

    bible   = load_bible_pairs(BIBLE_PAIRS_PATH)
    print(f"  Bible          : {len(bible):>6,} paires")

    dico    = load_dict_pairs(DICT_PAIRS_PATH)
    print(f"  Dictionnaire   : {len(dico):>6,} paires")

    lexicon = load_lexicon_pairs(LEXICON_PATH)
    print(f"  Lexique Sara   : {len(lexicon):>6,} paires")

    all_pairs = bible + dico + lexicon
    print(f"  TOTAL          : {len(all_pairs):>6,} paires")

    random.seed(SEED)
    random.shuffle(all_pairs)

    split = int(len(all_pairs) * 0.9)
    train, val = all_pairs[:split], all_pairs[split:]
    print(f"  Train          : {len(train):>6,}")
    print(f"  Validation     : {len(val):>6,}")

    ALL_PAIRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALL_PAIRS_PATH, 'w', encoding='utf-8') as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
    with open(TRAIN_PATH, 'w', encoding='utf-8') as f:
        for p in train:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
    with open(VAL_PATH, 'w', encoding='utf-8') as f:
        for p in val:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    print(f"\n  -> {ALL_PAIRS_PATH}")
    print(f"  -> {TRAIN_PATH}")
    print(f"  -> {VAL_PATH}")

    print("\n=== Corpus monolingue Sar ===")

    sardc = load_sardc_sentences(SARDC_RAW_PATH)
    print(f"  SARDC Bible    : {len(sardc):>6,} phrases")

    cosmo = load_cosmo_sentences(COSMO_PATH)
    print(f"  Cosmogonie     : {len(cosmo):>6,} phrases")

    sar_side = [_clean(p['sar']) for p in all_pairs]
    all_mono = sardc + sar_side + cosmo

    seen: set[str] = set()
    unique: list[str] = []
    for s in all_mono:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    print(f"  Total unique   : {len(unique):>6,} phrases ({len(all_mono)-len(unique):,} doublons supprimés)")
    print(f"  Total mots     : {sum(len(s.split()) for s in unique):>6,}")

    MONOLINGUAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MONOLINGUAL_PATH.write_text('\n'.join(unique) + '\n', encoding='utf-8')
    print(f"\n  -> {MONOLINGUAL_PATH}")


if __name__ == '__main__':
    main()
