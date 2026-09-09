import csv
import json
import re
from pathlib import Path
from unicodedata import normalize

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

PDF_PATH = Path("data/raw/dictionary/sar_dictionary.pdf")
RAW_TEXT_PATH = Path("data/intermediate/dictionary/sar_dictionary_raw.txt")
STRUCTURED_PATH = Path("data/intermediate/dictionary/sar_dictionary_structured.json")
PAIRS_OUTPUT_PATH = Path("data/processed/dictionary/sar_dictionary_example_pairs.csv")

POS_TAGS = {'AV', 'VT', 'VI', 'N', 'ADJ', 'ADV', 'CNJ', 'AUX', 'V', 'PRA', 'LOC', 'INS', 'INJ', 'INT', 'C', 'ID'}

SAR_EXAMPLE_PATTERN = r'[ɨəɔɛɲʉŋƖḭḛḿṵāīēōūìîǹ]'

# Corrections for PDF font encoding errors.
# The PDF embeds SILDoulosIPA93 and SaraBagirmiTimes with broken/incomplete
# ToUnicode CMaps, causing PyMuPDF to emit wrong codepoints.
CHAR_CORRECTIONS = {
    # Compound corrections MUST come before their base-char corrections.
    # The PDF encodes ɛ̄ as two glyphs: Odia E (U+0B0E) + combining macron (U+0304).
    # Our base correction '਎'→ɛ would turn that into ɛ̄; intercept the pair first.
    '଎̄': 'ə́',  # U+0B0E + U+0304 → ə+acute: open-e+macron is ə+high-tone in Sar
    'ɛ̄': 'ə́',      # fallback: ɛ+macron → ə+acute (if source already has ɛ, e.g. SARDC)
    'ᵼ': 'ə',      # ᵼ U+1D7C (iota-stroke) misread by PDF → ə U+0259 (schwa, standard Sar phoneme)
    'ᶉ': 'r',      # ᶉ U+1D89 (r-fishhook) SILDoulosIPA93 CMap error → plain r
    'ň': 'n̄',  # ň U+0148 (n-caron) misread → n̄ (n + combining macron, mid-tone n)
    '଎': 'ɛ',      # Odia E U+0B0E (misread) → ɛ U+025B (open-e vowel, absent from CMap)
    'ӯ': 'ȳ',      # Cyrillic ū (misread) → ȳ U+0233 (y+macron, CMap error)
    'ࢲ': '̰',  # Arabic char (SaraBagirmiTimes CMap error) → combining tilde below (nasalization)
    'ࢳ': '̰',  # Arabic char (SaraBagirmiTimes CMap error) → combining tilde below
    '': '',        # PUA artifacts from SIL Doulos IPA 93 font → remove
    '': '',
    '': '',
    '': '',
    '': '',
    '': '',
    '': '',
    '': '',
}


def fix_char_encoding(text: str) -> str:
    for wrong, correct in CHAR_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    text = re.sub(r' {2,}', ' ', text)
    return normalize('NFC', text)


def extract_pdf_text(pdf_path: str) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install with: pip install pymupdf")

    text_content = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        if text.strip():
            text_content.append(f"--- PAGE {page_num} ---\n{text}")
    return fix_char_encoding("\n".join(text_content))


def repair_line_breaks(text: str) -> str:
    text = re.sub(r'([^\-\s])-\n([^\-\s])', r'\1\2', text)
    text = re.sub(r'\n+', '\n', text)
    return text


def find_dictionary_start(text: str) -> int:
    for i, line in enumerate(text.splitlines()):
        if re.search(r'^Sar\s*-\s*Fran[çc]ais', line):
            return i
    return 0


def clean_line(line: str) -> str:
    line = normalize('NFC', line)
    line = re.sub(r'^\d+\s+', '', line)
    return line.strip()


def extract_pos_and_gloss(line: str) -> tuple[str, str] | None:
    match = re.match(r'^([A-Z]+)\s+(.+)', line, re.DOTALL)
    if not match:
        return None

    pos = match.group(1).strip()
    rest = match.group(2).strip()

    if pos not in POS_TAGS:
        return None

    first_period_idx = rest.find('.')
    if first_period_idx > 0:
        gloss = rest[:first_period_idx].strip()
    else:
        gloss = rest.strip()

    if len(gloss) > 250:
        rest_after = rest[first_period_idx + 1:].strip() if first_period_idx > 0 else ""
        if rest_after:
            second_period = rest_after.find('.')
            if 0 < second_period < 150:
                gloss = gloss + ". " + rest_after[:second_period]

    gloss = gloss.rstrip('.,;:!?() ')
    return (pos, gloss) if gloss and len(gloss) > 2 else None


def extract_examples(definition_text: str) -> list[dict]:
    examples = []
    sentences = re.findall(r'[^.!?]+[.!?]', definition_text)
    if not sentences and definition_text.strip():
        sentences = [definition_text.strip()]

    sentences = [s.strip() for s in sentences if s.strip()]
    i = 0

    while i < len(sentences):
        sent = sentences[i]
        is_sar = bool(re.search(SAR_EXAMPLE_PATTERN, sent))

        if is_sar and i + 1 < len(sentences):
            next_sent = sentences[i + 1]
            next_is_sar = bool(re.search(SAR_EXAMPLE_PATTERN, next_sent))

            if not next_is_sar and len(next_sent) > 4:
                sar_clean = sent.rstrip('.,!? ')
                fr_clean = next_sent.rstrip('.,!? ')

                if len(sar_clean) > 5 and len(fr_clean) > 5:
                    examples.append({'sar': sar_clean, 'fr': fr_clean})
                    i += 2
                    continue

        i += 1

    return examples


def is_pos_line(line: str) -> bool:
    return bool(re.match(r'^[A-Z]{1,4}\s+', line))


def is_headword_line(line: str, next_line: str | None) -> bool:
    if not line or '[' not in line or ']' not in line:
        return False
    if line.startswith(('Expr:', 'Expr ', 'Syn:')):
        return False
    if is_pos_line(line):
        return False
    if next_line is None:
        return False
    if not is_pos_line(next_line):
        return False
    return len(line) < 45


def group_entries_by_headword(lines: list[str]) -> list[tuple[str, list[str]]]:
    groups = []
    current_headword = None
    current_lines: list[str] = []

    for idx, line in enumerate(lines):
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None
        if is_headword_line(line, next_line):
            if current_headword:
                groups.append((current_headword, current_lines))
            current_headword = line.strip()
            current_lines = []
            continue

        if current_headword:
            current_lines.append(line)

    if current_headword:
        groups.append((current_headword, current_lines))

    return groups


def normalize_headword(headword: str) -> str:
    return normalize('NFC', headword.split('[')[0].strip())


def extract_structured_entries(raw_text: str) -> list[dict]:
    raw_text = repair_line_breaks(raw_text)
    start_index = find_dictionary_start(raw_text)
    if start_index > 0:
        raw_text = '\n'.join(raw_text.splitlines()[start_index:])

    lines = [clean_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line and not line.startswith('---')]

    entries = []
    groups = group_entries_by_headword(lines)

    for headword, def_lines in groups:
        blocks: list[list[str]] = []
        for line in def_lines:
            if is_pos_line(line):
                blocks.append([line])
            elif blocks:
                blocks[-1].append(line)

        for block in blocks:
            result = extract_pos_and_gloss(block[0])
            if not result:
                continue

            pos, gloss = result
            full_text = ' '.join(block)
            examples = extract_examples(full_text)
            entries.append({
                'id': f'dict_{len(entries) + 1:05d}',
                'headword': headword,
                'normalized_headword': normalize_headword(headword),
                'pos': pos,
                'gloss_fr': gloss,
                'examples': examples,
                'source': 'sar_dictionary'
            })

    return entries


def extract_dictionary_example_pairs(entries: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for entry in entries:
        for example in entry.get('examples', []):
            sar = example.get('sar', '').strip()
            fr = example.get('fr', '').strip()
            if sar and fr:
                pairs.append((sar, fr))
    return pairs


def write_example_pairs_csv(path: Path, pairs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['sar', 'fr'])
        for sar, fr in pairs:
            writer.writerow([sar, fr])
