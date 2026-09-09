#!/usr/bin/env python3
"""Train and apply a SentencePiece tokenizer on corpus files.

Usage examples:
  Train a model on combined corpora:
    python scripts/tokenize.py train --inputs data/processed/sar_monolingual.txt --model-prefix models/sp --vocab-size 8000

  Encode a jsonl parallel file (adds `.tok.jsonl`):
    python scripts/tokenize.py encode --model models/sp.model --input data/processed/sar_fr_train.jsonl
"""
import argparse
import io
import json
import os
import tempfile
from typing import List

try:
    import sentencepiece as spm
except Exception:
    spm = None


def train_sentencepiece(input_files: List[str], model_prefix: str, vocab_size: int, model_type: str = "unigram"):
    if spm is None:
        raise RuntimeError("sentencepiece is not installed. Install with `pip install sentencepiece`")

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tmp:
        for path in input_files:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    tmp.write(line)
        tmp_path = tmp.name

    cmd = (
        f"--input={tmp_path} --model_prefix={model_prefix} --vocab_size={vocab_size}"
        f" --character_coverage=1.0 --model_type={model_type} --unk_id=0 --pad_id=1 --bos_id=-1 --eos_id=-1"
    )
    spm.SentencePieceTrainer.Train(cmd)
    os.remove(tmp_path)
    print(f"Trained SentencePiece model: {model_prefix}.model ({vocab_size} tokens)")


def encode_jsonl(input_path: str, model_path: str, output_path: str = None, fields: List[str] = None):
    if spm is None:
        raise RuntimeError("sentencepiece is not installed. Install with `pip install sentencepiece`")

    sp = spm.SentencePieceProcessor()
    sp.Load(model_path)

    if output_path is None:
        output_path = input_path + ".tok.jsonl"

    with open(input_path, "r", encoding="utf-8") as inf, open(output_path, "w", encoding="utf-8") as outf:
        for line in inf:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if fields is None:
                # default: look for 'sar' and 'fr'
                fields = [k for k in ("sar", "fr") if k in obj]
            for f in fields:
                if f in obj:
                    toks = sp.EncodeAsPieces(obj[f])
                    obj[f + "_tok"] = " ".join(toks)
                    obj[f + "_ids"] = sp.EncodeAsIds(obj[f])
            outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Wrote tokenized output to {output_path}")


def encode_csv(input_path: str, model_path: str, output_path: str = None, text_col: str = "text"):
    import csv

    if spm is None:
        raise RuntimeError("sentencepiece is not installed. Install with `pip install sentencepiece`")

    sp = spm.SentencePieceProcessor()
    sp.Load(model_path)

    if output_path is None:
        output_path = input_path + ".tok.csv"

    with open(input_path, "r", encoding="utf-8", newline='') as inf, open(output_path, "w", encoding="utf-8", newline='') as outf:
        reader = csv.DictReader(inf)
        fieldnames = reader.fieldnames + [text_col + "_tok"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            txt = row.get(text_col, "")
            toks = sp.EncodeAsPieces(txt)
            row[text_col + "_tok"] = " ".join(toks)
            writer.writerow(row)
    print(f"Wrote tokenized CSV to {output_path}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    t = sub.add_parser("train")
    t.add_argument("--inputs", nargs="+", required=True, help="Input files to train on (text files or jsonl with a text field)")
    t.add_argument("--model-prefix", required=True)
    t.add_argument("--vocab-size", type=int, default=8000)
    t.add_argument("--model-type", choices=["unigram", "bpe", "word", "char"], default="unigram")

    e = sub.add_parser("encode")
    e.add_argument("--model", required=True)
    e.add_argument("--input", required=True)
    e.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    e.add_argument("--text-field", default="text", help="CSV text column or JSONL field (defaults: 'text' for CSV, 'sar'/'fr' for JSONL)")

    args = p.parse_args()
    if args.cmd == "train":
        # expand jsonl inputs to plain text if needed
        files = []
        for path in args.inputs:
            if path.endswith(".jsonl"):
                # extract textual fields into temp file
                with open(path, "r", encoding="utf-8") as f:
                    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tmp:
                        for line in f:
                            try:
                                obj = json.loads(line)
                            except Exception:
                                continue
                            for k in ("sar", "fr", "text"):
                                if k in obj:
                                    tmp.write(obj[k] + "\n")
                        files.append(tmp.name)
            else:
                files.append(path)
        train_sentencepiece(files, args.model_prefix, args.vocab_size, args.model_type)
    elif args.cmd == "encode":
        if args.format == "jsonl":
            encode_jsonl(args.input, args.model)
        else:
            encode_csv(args.input, args.model, text_col=args.text_field)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
