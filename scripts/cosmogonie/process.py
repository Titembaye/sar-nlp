"""Découpe le texte de la cosmogonie sar (monolingue) en phrases et en paragraphes.

Source : `data/raw/cosmogonie/cosmogonie_sar_texte.txt`, texte extrait du PDF
"mwm_Cosmogonie_Sar_2015.pdf" (© OSSEC 2015), avec des marqueurs `--- Page n ---`
conservés dans le fichier texte pour tracer la pagination d'origine.

Produit deux granularités à partir du même texte : `cosmogonie_sentences.jsonl`
(une phrase par ligne, pour le corpus monolingue sar) et
`cosmogonie_paragraphs.jsonl` (unité plus longue, utile si le découpage en
phrases perd du contexte narratif). Il n'y a pas de traduction française
disponible pour ce texte — c'est une source purement monolingue sar.

Usage :
    python -m scripts.cosmogonie.process
"""
import json
import re
from pathlib import Path

INPUT_FILE = Path("data/raw/cosmogonie/cosmogonie_sar_texte.txt")
OUTPUT_SENTENCES = Path("data/processed/cosmogonie/cosmogonie_sentences.jsonl")
OUTPUT_PARAGRAPHS = Path("data/processed/cosmogonie/cosmogonie_paragraphs.jsonl")

PAGE_MARKER = re.compile(r'^---\s*Page\s*(\d+)\s*---$')
MIN_SENTENCE_CHARS = 8  # en dessous, probablement un artefact de découpage, pas une vraie phrase


def _iter_clean_lines(text: str):
    """Yield (page, line) — drops header comments and page-marker lines."""
    page = 0
    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        m = PAGE_MARKER.match(line)
        if m:
            page = int(m.group(1))
            continue
        yield page, line


def _split_sentences(line: str) -> list[str]:
    """Split one text line into sentences on .!? boundaries and dialogue dashes."""
    # Normalise multiple dashes/quotes used as dialogue markers
    line = re.sub(r'^\s*["\-]+\s*', '', line)
    # Split on sentence-final punctuation followed by whitespace
    raw = re.split(r'(?<=[.!?])\s+', line)
    # Also split on dialogue dash: " - " in the middle of a line
    sentences = []
    for seg in raw:
        parts = re.split(r'\s+-\s+', seg)
        sentences.extend(parts)
    return [s.strip().strip('"').strip("'").strip() for s in sentences
            if len(s.strip()) >= MIN_SENTENCE_CHARS]


def extract_sentences(text: str) -> list[dict]:
    """Découpe tout le texte en phrases (via `_iter_clean_lines` + `_split_sentences`),
    chacune associée à son numéro de page d'origine."""
    entries = []
    sid = 0
    for page, line in _iter_clean_lines(text):
        for sent in _split_sentences(line):
            sid += 1
            entries.append({
                'id': f'cosmo_s_{sid:05d}',
                'text': sent,
                'page': page,
                'source': 'cosmogonie_sar',
            })
    return entries


def extract_paragraphs(text: str) -> list[dict]:
    """Regroupe les lignes consécutives (séparées par une ligne vide ou un
    changement de page) en paragraphes, chacun rattaché à sa page de départ."""
    current_page = 0
    paragraphs: list[tuple[int, list[str]]] = []
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            if current:
                paragraphs.append((current_page, current))
                current = []
            continue
        m = PAGE_MARKER.match(stripped)
        if m:
            if current:
                paragraphs.append((current_page, current))
                current = []
            current_page = int(m.group(1))
            continue
        current.append(stripped)

    if current:
        paragraphs.append((current_page, current))

    return [
        {'id': f'cosmo_p_{i:05d}', 'text': ' '.join(lines), 'page': page, 'source': 'cosmogonie_sar'}
        for i, (page, lines) in enumerate(paragraphs, 1)
    ]


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Écrit une liste de dicts en JSONL (un objet JSON par ligne)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def main(
    input_path: Path = INPUT_FILE,
    sentences_path: Path = OUTPUT_SENTENCES,
    paragraphs_path: Path = OUTPUT_PARAGRAPHS,
) -> tuple[Path, Path]:
    """Lit le texte source et écrit les deux granularités (phrases, paragraphes)."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    text = input_path.read_text(encoding='utf-8')

    sentences = extract_sentences(text)
    _write_jsonl(sentences_path, sentences)
    print(f"  {len(sentences):,} sentences -> {sentences_path}")

    paragraphs = extract_paragraphs(text)
    _write_jsonl(paragraphs_path, paragraphs)
    print(f"  {len(paragraphs):,} paragraphs -> {paragraphs_path}")

    return sentences_path, paragraphs_path


if __name__ == '__main__':
    main()
