"""
extract_cosmogonie.py

Extraction du texte Sar depuis la cosmogonie.

Usage:
    python scripts/extract_cosmogonie.py

Résultat:
    data/processed/cosmogonie_structured.json
"""

import json
from pathlib import Path

INPUT_FILE = Path("data/processed/cosmogonie_sar_texte.txt")
OUTPUT_FILE = Path("data/processed/cosmogonie_structured.json")


def main():
    if not INPUT_FILE.exists():
        print(f"File not found: {INPUT_FILE}")
        return
    
    print("Extracting cosmogonie...")
    
    with open(INPUT_FILE, encoding='utf-8') as f:
        text = f.read()
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    entries = []
    for i, para in enumerate(paragraphs, 1):
        entry = {
            'id': f'cosmo_{i:05d}',
            'text': para,
            'source': 'cosmogonie_sar'
        }
        entries.append(entry)
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(entries)} paragraphs → {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
