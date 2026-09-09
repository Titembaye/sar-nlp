"""
Pipeline dictionnaire complet : PDF → texte brut → structuré → paires CSV.

Usage:
    python -m scripts.dictionary.pipeline
"""

from .extract import main as extract
from .process import main as process
from .export import main as export


def main() -> None:
    print("=== Step 1: Extract raw text from PDF ===")
    extract()

    print()
    print("=== Step 2: Parse structured entries ===")
    process()

    print()
    print("=== Step 3: Export example pairs ===")
    export()

    print()
    print("Dictionary pipeline complete.")


if __name__ == '__main__':
    main()
