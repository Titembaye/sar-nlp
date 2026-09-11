"""Étape 1/3 du pipeline dictionnaire : PDF source -> texte brut corrigé.

Extrait le texte du PDF page par page (PyMuPDF) et applique les corrections
d'encodage de `common.CHAR_CORRECTIONS` (voir ce module pour le détail des
erreurs de CMap qu'elles réparent).

Usage :
    python -m scripts.dictionary.extract
"""
from pathlib import Path

from .common import PDF_PATH, RAW_TEXT_PATH, extract_pdf_text


def main() -> Path:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    RAW_TEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw_text = extract_pdf_text(str(PDF_PATH))

    with open(RAW_TEXT_PATH, 'w', encoding='utf-8') as f:
        f.write(raw_text)

    print(f"Raw text extracted -> {RAW_TEXT_PATH}")
    return RAW_TEXT_PATH


if __name__ == '__main__':
    main()
