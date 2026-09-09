"""
Extraction du lexique SaraLanguagesLexicon.pdf → paires multilingues.
Applique la table de correction SaraFont complète établie en juin 2026.

Usage:
    python -m scripts.sara_lexicon.extract

Sorties :
  data/processed/sara_lexicon/sara_multilingual_long.csv  — toutes langues
  data/processed/sara_lexicon/sar_fr_pairs.csv / .jsonl   — Sar–Français
  data/processed/sara_lexicon/sar_en_pairs.csv / .jsonl   — Sar–Anglais
"""

import csv
import json
import re
import sys
from pathlib import Path

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PDF_PATH = Path("data/raw/sara_lexicon/sara_languages_lexicon.pdf")
OUT_DIR  = Path("data/processed/sara_lexicon")

# ─────────────────────────────────────────────────────────────────────────────
# Table de correction SaraFont (WinAnsiEncoding → IPA/Unicode Sar réel)
# Établie par inspection visuelle PDF + comparaison inter-langues + corpus Bible
# ─────────────────────────────────────────────────────────────────────────────
_SARA_FONT_MAP = str.maketrans({
    # ── Mapping existant (hérité, certains corrigés) ─────────────────────
    '¡': 'ĩ',    # 0xA1  i nasalisé
    '¼': 'ɔ̃',   # 0xBC  ɔ nasalisé
    'È': 'ɾ',    # 0xC8  flap r (rétroflexe)
    'Ï': 'ḛ',    # 0xCF  e+tilde-bas (probable; ancien: ɛ̃ nasalisé)
    'Ÿ': 'ḛ',    # 0x178 e+tilde-bas ton bas (ancien: ɛ̃)
    'Ð': 'ə',    # 0xD0  schwa
    'æ': 'ə',    # 0xE6  schwa (variante très fréquente)
    'ä': 'ā',    # 0xE4  a ton moyen
    'ö': 'ō',    # 0xF6  o ton moyen
    'û': 'ɔ',    # 0xFB  ɔ ouvert
    'î': 'ɔ',    # 0xEE  ɔ ouvert (kîdə́→kɔdə́ tambour; corpus confirmé)
    'ü': 'ū',    # 0xFC  u ton moyen (kübə̄→kūbə̄ habit; 246x corpus)
    'ë': 'ē',    # 0xEB  e ton moyen (ɓë→ɓē village; 2381x corpus)
    'ÿ': 'ȳ',    # 0xFF  y ton moyen
    'ß': 'ɓ',    # 0xDF  b implosif
    '÷': 'ɗ',    # 0xF7  d implosif
    # ── Corrigés cette session ───────────────────────────────────────────
    'Õ': 'ə́',   # 0xD5  schwa ton haut  (ancien: '†' placeholder)
    '¸': 'ə̄',   # 0xB8  schwa ton moyen (ancien: 'ā' par erreur)
    # ── Nouveaux (établis par corpus + comparaison inter-langues) ────────
    # Voyelle o̰ = "on" (3 variantes typographiques du même phonème)
    'Å': 'o̰',   # 0xC5
    'Ç': 'o̰',   # 0xC7
    'ø': 'o̰',   # 0xF8
    # ɔ̄ (ɔ ton moyen, 2 variantes)
    'ç': 'ɔ̄',   # 0xE7
    '¦': 'ɔ̄',   # 0xA6
    # ɔ ton bas
    'ƒ': 'ɔ',    # 0x192
    # ā (4 variantes typographiques)
    'þ': 'ā',    # 0xFE
    'º': 'ā',    # 0xBA
    'ª': 'ā',    # 0xAA
    '¬': 'ī',    # 0xAC  (était 'ā' — corrigé : kāyā→kīyā pour karité)
    # l (4 variantes)
    '£': 'l',    # 0xA3
    '¥': 'l',    # 0xA5
    '°': 'l',    # 0xB0
    '•': 'l',    # 0x2022
    # r (3 variantes)
    '®': 'r',    # 0xAE
    'Ê': 'r',    # 0xCA
    '±': 'r',    # 0xB1
    # m
    '¯': 'm',    # 0xAF
    # n (4 variantes)
    'ñ': 'n',    # 0xF1
    'Ñ': 'n',    # 0xD1
    'µ': 'n',    # 0xB5
    '©': 'n',    # 0xA9
    # ī (3 variantes)
    'ï': 'ī',    # 0xEF
    '‡': 'ī',    # 0x2021
    '«': 'ī',    # 0xAB
    # w, y
    'Û': 'w',    # 0xDB
    'Ø': 'y',    # 0xD8
    # b implosif (variante)
    '€': 'ɓ',    # 0x20AC
    # ── Non identifiés — laissés tels quels ─────────────────────────────
    # '»' 0xBB  suffixe possessif 1SG (ex: -»  = mon/ma)
    # '²' 0xB2  suffixe oblique 3SG (ex: -²  = avec lui)
    # 'Ë' 0xCB  inconnu (ex: mātā-kāË = callosité)
    # 'Þ' 0xDE  inconnu (ex: náÞ = pêcheur)
})

SARA_LANGS = {
    "Beb": "Bebote",
    "Bd":  "Bediondo",
    "Db":  "Daba",
    "Gor": "Gor",
    "Gu":  "Gulay",
    "KbN": "Kaba_Na",
    "Kbb": "Kaba",
    "Lk":  "Laka",
    "Mb":  "Mbay",
    "Mo":  "Mango",
    "Nar": "Nar",
    "Ngb": "Ngambay",
    "Sr":  "Sar",
    "NgT": "Ngam",
}

_CODES_RE   = "|".join(re.escape(c) for c in SARA_LANGS)
_TRANS_PAT  = re.compile(rf'(?:{_CODES_RE})=')
_PAIR_PAT   = re.compile(rf'({_CODES_RE})=(\S+)')
_FR_HDR_PAT = re.compile(r'^(Français\s*[–\-]\s*Langues Sara|Français\s*[–\-]?|Langues Sara)$', re.IGNORECASE)
_EN_HDR_PAT = re.compile(r'^(English\s*[–\-]\s*Sara Languages|English\s*[–\-]?|Sara Languages)$', re.IGNORECASE)
_SKIP_PAT   = re.compile(
    r'^(\d+|Lexique|Acknowledgements|Abbreviations)$',
    re.IGNORECASE,
)


def fix_sara(word: str) -> str:
    return word.translate(_SARA_FONT_MAP)


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def parse_column(text: str, src_lang: str = 'fr') -> tuple[list[dict], str]:
    entries = []
    current_hw = None
    current_tr: dict[str, str] = {}
    current_lang = src_lang

    for raw in text.split('\n'):
        line = norm(raw)
        if not line or _SKIP_PAT.match(line):
            continue

        if _FR_HDR_PAT.match(line):
            current_lang = 'fr'
            continue
        if _EN_HDR_PAT.match(line):
            current_lang = 'en'
            continue

        if _TRANS_PAT.search(line):
            for m in _PAIR_PAT.finditer(line):
                code, word = m.group(1), m.group(2)
                if code in SARA_LANGS and word:
                    current_tr[code] = fix_sara(word)
        else:
            if current_hw is not None:
                entries.append({'src_lang': current_lang, 'headword': current_hw, **current_tr})
            current_hw = line
            current_tr = {}

    if current_hw is not None and current_tr:
        entries.append({'src_lang': current_lang, 'headword': current_hw, **current_tr})

    return entries, current_lang


def split_columns(page):
    W = page.width
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return '', ''

    mid = W * 0.50
    left_words  = [w for w in words if (w['x0'] + w['x1']) / 2 < mid]
    right_words = [w for w in words if (w['x0'] + w['x1']) / 2 >= mid]

    def words_to_text(wlist):
        if not wlist:
            return ''
        wlist = sorted(wlist, key=lambda w: (round(w['top'] / 5) * 5, w['x0']))
        lines, cur_y, cur_line = [], None, []
        for w in wlist:
            y = round(w['top'] / 5) * 5
            if cur_y is None or abs(y - cur_y) <= 5:
                cur_line.append(w['text'])
                cur_y = y
            else:
                lines.append(' '.join(cur_line))
                cur_line = [w['text']]
                cur_y = y
        if cur_line:
            lines.append(' '.join(cur_line))
        return '\n'.join(lines)

    return words_to_text(left_words), words_to_text(right_words)


def extract() -> tuple[list[dict], list[dict], list[dict]]:
    raw_entries: list[dict] = []
    current_lang = 'fr'

    with pdfplumber.open(PDF_PATH) as pdf:
        pages = pdf.pages[9:]
        total = len(pages)
        print(f'Extraction de {total} pages...')

        for i, page in enumerate(pages, start=10):
            left, right = split_columns(page)
            for col in (left, right):
                entries, current_lang = parse_column(col, current_lang)
                raw_entries.extend(entries)

            if i % 30 == 0 or i == total + 9:
                print(f'  page {i}/{total + 9}  — {len(raw_entries)} entrées brutes')

    # Fusionner les entrées dupliquées (même headword + src_lang)
    merged: dict[tuple, dict] = {}
    for e in raw_entries:
        key = (e['src_lang'], e['headword'])
        if key not in merged:
            merged[key] = {'src_lang': e['src_lang'], 'headword': e['headword']}
        for k, v in e.items():
            if k not in ('src_lang', 'headword') and v:
                merged[key][k] = v

    entries = list(merged.values())
    fr_count = sum(1 for e in entries if e['src_lang'] == 'fr')
    en_count = sum(1 for e in entries if e['src_lang'] == 'en')
    print(f'\n{len(entries)} termes distincts : {fr_count} français, {en_count} anglais.')

    # Format long — toutes langues
    all_pairs: list[dict] = []
    for e in entries:
        src_lang_label = 'French' if e['src_lang'] == 'fr' else 'English'
        for code, lang in SARA_LANGS.items():
            word = e.get(code, '').strip()
            if word:
                all_pairs.append({
                    'source_lang': src_lang_label,
                    'source_word': e['headword'],
                    'target_lang': lang,
                    'target_word': word,
                    'source_file': 'SaraLanguagesLexicon.pdf',
                })

    sar_fr_pairs = [p for p in all_pairs if p['target_lang'] == 'Sar' and p['source_lang'] == 'French']
    sar_en_pairs = [p for p in all_pairs if p['target_lang'] == 'Sar' and p['source_lang'] == 'English']
    return all_pairs, sar_fr_pairs, sar_en_pairs


def save(all_pairs: list[dict], sar_fr_pairs: list[dict], sar_en_pairs: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ['source_lang', 'source_word', 'target_lang', 'target_word', 'source_file']
    UNKNOWN = {'»', '²', 'Ë', 'Þ'}

    path_multi = OUT_DIR / 'sara_multilingual_long.csv'
    with open(path_multi, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_pairs)
    print(f'  {len(all_pairs):5} paires  -> {path_multi}')

    def write_pairs(pairs, path_csv, path_jsonl, src_lang_code):
        with open(path_csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(pairs)
        print(f'  {len(pairs):5} paires  -> {path_csv}')

        clean = [p for p in pairs if not any(c in p['target_word'] for c in UNKNOWN)]
        with open(path_jsonl, 'w', encoding='utf-8') as f:
            for p in clean:
                f.write(json.dumps({
                    'source': p['source_word'],
                    'target': p['target_word'],
                    'source_lang': src_lang_code,
                    'target_lang': 'sar',
                }, ensure_ascii=False) + '\n')
        print(f'  {len(clean):5} paires  -> {path_jsonl}  ({len(pairs)-len(clean)} exclues: chars inconnus)')

        unresolved = [(p['source_word'], p['target_word'], ch)
                      for p in pairs for ch in p['target_word'] if ch in UNKNOWN]
        if unresolved:
            seen: set = set()
            print('  Chars non mappés restants :')
            for src, sar, ch in unresolved[:10]:
                if (src, ch) not in seen:
                    print(f'    {ch!r} dans "{sar}" (src: "{src}")')
                    seen.add((src, ch))

    write_pairs(sar_fr_pairs, OUT_DIR / 'sar_fr_pairs.csv', OUT_DIR / 'sar_fr_pairs.jsonl', 'fr')
    write_pairs(sar_en_pairs, OUT_DIR / 'sar_en_pairs.csv', OUT_DIR / 'sar_en_pairs.jsonl', 'en')


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
    all_pairs, sar_fr_pairs, sar_en_pairs = extract()
    print('\nSauvegarde...')
    save(all_pairs, sar_fr_pairs, sar_en_pairs)
    print('\nTerminé.')


if __name__ == '__main__':
    main()
