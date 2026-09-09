#!/usr/bin/env python3
"""Évalue des tokeniseurs pré-entraînés sur le corpus Sar (et Français en référence).

Mesure, par tokeniseur et par langue :
  - round-trip : decode(encode(x)) == x  (fidélité encodeur/décodeur)
  - taux de <unk>
  - fertilité : sous-tokens / mot (séparé par espaces)
  - caractères par token, longueurs de séquence (p50/p95/max)
  - codepoints perdus lors du round-trip (avec comptes)

Usage :
  python -m scripts.eval_tokenizers                 # tous les tokeniseurs par défaut
  python -m scripts.eval_tokenizers --sample 2000   # échantillon plus petit
  python -m scripts.eval_tokenizers --models facebook/nllb-200-distilled-600M google/byt5-small
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data/processed/sar_fr_all_pairs.jsonl"
MONO = ROOT / "data/processed/sar_monolingual.txt"

DEFAULT_MODELS = [
    "facebook/nllb-200-distilled-600M",
    "facebook/mbart-large-50-many-to-many-mmt",
    "google/byt5-small",
    "xlm-roberta-base",
    "Davlan/afro-xlmr-base",
]

PUNCT = " \t\n.,;:!?()[]{}\"'«»=-–—…"


def load_corpus(sample: int | None):
    sar, fra = [], []
    with open(PAIRS, encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            sar.append(o["sar"].strip())
            fra.append(o["fr"].strip())
    with open(MONO, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                sar.append(s)
    sar = [unicodedata.normalize("NFC", s) for s in sar if s]
    fra = [unicodedata.normalize("NFC", s) for s in fra if s]
    if sample:
        sar = sar[:sample]
        fra = fra[:sample]
    return {"sar": sar, "fra": fra}


def nwords(s: str) -> int:
    return len([w for w in s.split() if w.strip(PUNCT)])


def evaluate(tok, sentences, unk_id):
    n = len(sentences)
    exact = 0
    exact_loose = 0
    sent_with_unk = 0
    total_tokens = 0
    total_words = 0
    total_chars = 0
    unk_tokens = 0
    lengths = []
    lost = collections.Counter()

    for s in sentences:
        ids = tok.encode(s, add_special_tokens=False)
        lengths.append(len(ids))
        total_tokens += len(ids)
        total_words += max(nwords(s), 1)
        total_chars += len(s)
        if unk_id is not None:
            u = ids.count(unk_id)
            unk_tokens += u
            if u:
                sent_with_unk += 1
        dec = tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        dec_n = unicodedata.normalize("NFC", dec)
        if dec_n == s:
            exact += 1
            exact_loose += 1
        else:
            if " ".join(dec_n.split()) == " ".join(s.split()):
                exact_loose += 1
            else:
                a = collections.Counter(s)
                b = collections.Counter(dec_n)
                for ch, cnt in a.items():
                    if b[ch] < cnt:
                        lost[ch] += cnt - b[ch]

    return {
        "sentences": n,
        "roundtrip_exact_%": round(100 * exact / n, 2),
        "roundtrip_loose_%": round(100 * exact_loose / n, 2),
        "sent_with_unk_%": round(100 * sent_with_unk / n, 3),
        "unk_per_1k_tokens": round(1000 * unk_tokens / total_tokens, 3) if total_tokens else 0,
        "fertility_tok_per_word": round(total_tokens / total_words, 3),
        "chars_per_token": round(total_chars / total_tokens, 3) if total_tokens else 0,
        "len_p50": int(statistics.median(lengths)),
        "len_p95": int(sorted(lengths)[int(0.95 * (len(lengths) - 1))]),
        "len_max": max(lengths),
        "lost_codepoints": {
            f"U+{ord(c):04X} {unicodedata.name(c, '?')}": cnt
            for c, cnt in lost.most_common(15)
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--sample", type=int, default=3000)
    ap.add_argument("--out", default=str(ROOT / "docs/TOKENIZATION_EVAL.md"))
    args = ap.parse_args()

    try:
        from transformers import AutoTokenizer
    except Exception as e:
        sys.exit(f"transformers requis : {e}")

    corpus = load_corpus(args.sample)
    print(f"Corpus : {len(corpus['sar'])} phrases Sar, {len(corpus['fra'])} phrases Fr "
          f"(échantillon={args.sample})\n")

    report = collections.OrderedDict()
    for name in args.models:
        print(f"=== {name} ===")
        try:
            tok = AutoTokenizer.from_pretrained(name)
        except Exception as e:
            print(f"  ÉCHEC chargement : {e}\n")
            report[name] = {"error": str(e)}
            continue
        unk_id = getattr(tok, "unk_token_id", None)
        entry = {"vocab_size": tok.vocab_size, "unk_token": tok.unk_token}
        for lang in ("sar", "fra"):
            res = evaluate(tok, corpus[lang], unk_id)
            entry[lang] = res
            print(f"  [{lang}] roundtrip={res['roundtrip_exact_%']}% "
                  f"(loose {res['roundtrip_loose_%']}%)  "
                  f"fertility={res['fertility_tok_per_word']}  "
                  f"unk/1k={res['unk_per_1k_tokens']}  "
                  f"p95_len={res['len_p95']}")
            if res["lost_codepoints"]:
                print(f"       perdus: {res['lost_codepoints']}")
        report[name] = entry
        print()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Évaluation des tokeniseurs sur le corpus Sar\n",
             f"_Échantillon : {args.sample} phrases par langue. Round-trip = decode(encode(x)) == x après NFC._\n",
             "\n| Tokeniseur | Lang | Round-trip exact | Round-trip loose | Fertilité (tok/mot) | <unk>/1k | p95 longueur |",
             "|---|---|---|---|---|---|---|"]
    for name, e in report.items():
        if "error" in e:
            lines.append(f"| {name} | — | ERREUR | | | | |")
            continue
        for lang in ("sar", "fra"):
            r = e[lang]
            lines.append(f"| {name} | {lang} | {r['roundtrip_exact_%']}% | {r['roundtrip_loose_%']}% "
                         f"| {r['fertility_tok_per_word']} | {r['unk_per_1k_tokens']} | {r['len_p95']} |")
    lines.append("\n## Détail (codepoints perdus)\n")
    for name, e in report.items():
        if "error" in e:
            continue
        lines.append(f"### {name}")
        for lang in ("sar", "fra"):
            lost = e[lang]["lost_codepoints"]
            lines.append(f"- **{lang}** : {lost if lost else 'aucune perte'}")
    lines.append("\n## JSON complet\n\n```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    lines.append("```")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapport écrit : {out}")


if __name__ == "__main__":
    main()
