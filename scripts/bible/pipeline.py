"""
Full Bible pipeline: fetch French Bible + align with SARDC.

Usage:
    python -m scripts.bible.pipeline
"""

from .fetch_french import main as fetch
from .align import main as align


def main() -> None:
    print("=== Step 1: French Bible ===")
    fetch()

    print()
    print("=== Step 2: Sar-French alignment ===")
    csv_out, jsonl_out = align()

    print()
    print("Bible pipeline complete.")
    print(f"  Pairs CSV  : {csv_out}")
    print(f"  Pairs JSONL: {jsonl_out}")


if __name__ == '__main__':
    main()
