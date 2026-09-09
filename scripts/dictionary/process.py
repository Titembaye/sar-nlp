import json
from pathlib import Path

from .common import RAW_TEXT_PATH, STRUCTURED_PATH, extract_structured_entries


def main(input_path: Path = RAW_TEXT_PATH, output_path: Path = STRUCTURED_PATH) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Raw text not found: {input_path}")

    with open(input_path, encoding='utf-8') as f:
        raw_text = f.read()

    entries = extract_structured_entries(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Structured entries written -> {output_path}")
    return output_path


if __name__ == '__main__':
    main()
