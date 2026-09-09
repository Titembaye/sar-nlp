from pathlib import Path
import json

from .common import STRUCTURED_PATH, PAIRS_OUTPUT_PATH, extract_dictionary_example_pairs, write_example_pairs_csv


def main(input_path: Path = STRUCTURED_PATH, output_path: Path = PAIRS_OUTPUT_PATH) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Structured data not found: {input_path}")

    with open(input_path, encoding='utf-8') as f:
        entries = json.load(f)

    pairs = extract_dictionary_example_pairs(entries)
    write_example_pairs_csv(output_path, pairs)

    print(f"Example pairs exported -> {output_path}")
    return output_path


if __name__ == '__main__':
    main()
