"""
Align SARDC Sar Bible with a French Bible translation, producing parallel verse pairs.

Usage:
    python -m scripts.bible.align

Prerequisites:
    1. data/raw/bible/sardc_corpus.jsonl  — already in repo
    2. data/raw/bible/french_bible_lsg.jsonl  — run scripts/bible/fetch_french.py

Output:
    data/processed/bible/sar_fr_bible_pairs.csv   (ref, sar, fr)
    data/processed/bible/sar_fr_bible_pairs.jsonl (ref, sar, fr)
"""

from pathlib import Path

from .common import (
    FRENCH_BIBLE_PATH,
    PAIRS_OUTPUT_PATH,
    SARDC_PATH,
    align_verses,
    load_french_bible,
    load_sardc,
    write_pairs_csv,
    write_pairs_jsonl,
)

JSONL_OUTPUT_PATH = PAIRS_OUTPUT_PATH.with_suffix('.jsonl')


def main(
    sardc_path: Path = SARDC_PATH,
    french_path: Path = FRENCH_BIBLE_PATH,
    csv_out: Path = PAIRS_OUTPUT_PATH,
    jsonl_out: Path = JSONL_OUTPUT_PATH,
) -> tuple[Path, Path]:
    if not sardc_path.exists():
        raise FileNotFoundError(f"SARDC corpus not found: {sardc_path}")
    if not french_path.exists():
        raise FileNotFoundError(
            f"French Bible not found: {french_path}\n"
            "Download Louis Segond from eBible.org and place it at that path.\n"
            "See scripts/bible/common.py for format details."
        )

    print("Loading SARDC corpus...")
    sar = load_sardc(sardc_path)
    print(f"  {len(sar):,} Sar verses loaded")

    print("Loading French Bible...")
    fr = load_french_bible(french_path)
    print(f"  {len(fr):,} French verses loaded")

    pairs = align_verses(sar, fr)
    missing_sar = len(fr) - len(pairs)
    missing_fr = len(sar) - len(pairs)
    print(f"  {len(pairs):,} aligned pairs ({missing_fr} Sar-only, {missing_sar} Fr-only)")

    # Drop pairs where Sar is too short relative to French (likely incomplete translations).
    # Threshold: Sar must have at least 30% as many words as French, and at least 3 words.
    before = len(pairs)
    pairs = [
        p for p in pairs
        if len(p['sar'].split()) >= 3
        and len(p['sar'].split()) / max(len(p['fr'].split()), 1) >= 0.30
    ]
    dropped = before - len(pairs)
    if dropped:
        print(f"  Dropped {dropped} low-quality pairs (Sar too short) -> {len(pairs):,} kept")

    write_pairs_csv(csv_out, pairs)
    print(f"  CSV  -> {csv_out}")

    write_pairs_jsonl(jsonl_out, pairs)
    print(f"  JSONL-> {jsonl_out}")

    return csv_out, jsonl_out


if __name__ == '__main__':
    main()
