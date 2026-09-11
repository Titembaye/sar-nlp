#!/usr/bin/env python3
"""Évalue des tokeniseurs pré-entraînés sur le corpus sar (et français en référence).

Objectif : mesurer, avant tout entraînement, si les tokeniseurs multilingues existants
préservent l'information portée par l'orthographe du sar (tons, nasalité) ou la
détruisent. Ces mesures documentent le problème posé par la thèse (cf. `docs/
TOKENIZATION.md`) ; elles ne portent que sur des tokeniseurs *pré-entraînés transférés*
au sar — un tokeniseur (BPE/WordPiece) entraîné directement sur le corpus sar n'aurait
pas de `<unk>`, mais resterait sujet aux problèmes de fragmentation et de cohérence des
frontières que la méthode de la thèse doit adresser.

Pour chaque tokeniseur et chaque langue, on calcule :
  - round-trip exact / "loose" : decode(encode(x)) == x, avant/après normalisation des
    espaces (fidélité encodeur-décodeur — un aller-retour non exact signifie une perte
    d'information, typiquement un caractère devenu `<unk>`)
  - taux de `<unk>` (tokens inconnus, pour 1000 tokens et part des phrases touchées)
  - fertilité : nombre de sous-tokens par mot (séparé par des espaces) — plus ce nombre
    est élevé, plus le tokeniseur fragmente la langue
  - caractères par token, longueurs de séquence en tokens (médiane, p95, max)
  - les codepoints Unicode perdus lors du round-trip, avec leur nombre d'occurrences

Reproductibilité :
  - L'échantillon est déterministe : les N premières phrases du fichier, dans l'ordre
    où elles apparaissent (pas de tirage aléatoire, donc pas de graine à fixer).
  - Les tokeniseurs sont chargés depuis le Hugging Face Hub via `AutoTokenizer.
    from_pretrained` ; leur comportement peut changer si le dépôt HF est mis à jour.
    Pour une reproduction stricte, épingler une révision avec `--revision <commit_sha>`
    ou fixer `transformers` à la version indiquée dans `requirements.txt`.
  - Les corpus source sont ceux de `data/processed/` (voir `data/README.md` pour les
    récupérer via DVC).

Usage :
  python -m scripts.eval_tokenizers                 # tous les tokeniseurs par défaut
  python -m scripts.eval_tokenizers --sample 2000   # échantillon plus petit (plus rapide)
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
PAIRS = ROOT / "data/processed/sar_fr_all_pairs.jsonl"   # paires sar-français alignées
MONO = ROOT / "data/processed/sar_monolingual.txt"        # sar seul (une phrase/ligne)

# Tokeniseurs comparés par défaut : NLLB (cible du fine-tuning), un modèle avec
# byte-fallback (mBART/mT5 family), un tokeniseur 100% octets (ByT5, sert de plafond
# théorique "zéro perte"), et deux tokeniseurs multilingues génériques dont un
# spécifiquement entraîné sur des langues africaines (AfroXLM-R).
DEFAULT_MODELS = [
    "facebook/nllb-200-distilled-600M",
    "facebook/mbart-large-50-many-to-many-mmt",
    "google/byt5-small",
    "xlm-roberta-base",
    "Davlan/afro-xlmr-base",
]

# Ponctuation retirée avant de compter les "mots" d'une phrase (séparation naïve par
# espaces : suffisant ici, le but est de comparer des fertilités entre tokeniseurs sur
# la même segmentation en mots, pas de faire une tokenisation linguistique du sar).
PUNCT = " \t\n.,;:!?()[]{}\"'«»=-–—…"


def load_corpus(sample: int | None) -> dict[str, list[str]]:
    """Charge le corpus sar-français et le complète avec le monolingue sar.

    Args:
        sample: si fourni, ne garde que les `sample` premières phrases de chaque
            langue (troncature déterministe, pas d'échantillonnage aléatoire).

    Returns:
        Un dict à deux clés, "sar" et "fr", chacune une liste de phrases normalisées
        en Unicode NFC (forme de composition canonique — cf. docs/TOKENIZATION.md sur
        l'importance de la normalisation pour les diacritiques du sar).
    """
    sar, fr = [], []
    with open(PAIRS, encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            sar.append(o["sar"].strip())
            fr.append(o["fr"].strip())
    # Le monolingue sar (Bible, cosmogonie, exemples du dictionnaire) élargit
    # l'échantillon côté sar sans équivalent français correspondant.
    with open(MONO, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                sar.append(s)
    sar = [unicodedata.normalize("NFC", s) for s in sar if s]
    fr = [unicodedata.normalize("NFC", s) for s in fr if s]
    if sample:
        sar = sar[:sample]
        fr = fr[:sample]
    return {"sar": sar, "fr": fr}


def nwords(s: str) -> int:
    """Compte les "mots" d'une phrase par simple séparation sur les espaces,
    en ignorant les tokens réduits à de la ponctuation pure."""
    return len([w for w in s.split() if w.strip(PUNCT)])


def evaluate(tok, sentences: list[str], unk_id: int | None) -> dict:
    """Calcule les métriques de fidélité et de fragmentation d'un tokeniseur.

    Args:
        tok: un tokeniseur Hugging Face déjà chargé (`AutoTokenizer.from_pretrained`).
        sentences: les phrases à encoder, normalisées en NFC.
        unk_id: l'id du token `<unk>` du tokeniseur, ou None s'il n'en a pas
            (cas des tokeniseurs à niveau octet comme ByT5, qui ne perdent jamais
            d'information puisque tout caractère se décompose en octets connus).

    Returns:
        Un dict de métriques agrégées (voir le docstring du module) plus le détail
        des codepoints Unicode perdus lors du round-trip, pour diagnostic.
    """
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

        # Round-trip : on redécode les ids et on renormalise en NFC avant de comparer,
        # pour ne pas compter comme "perte" un simple changement de forme Unicode
        # (ex. voyelle + diacritique combinant vs. caractère précomposé équivalent).
        dec = tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        dec_n = unicodedata.normalize("NFC", dec)
        if dec_n == s:
            exact += 1
            exact_loose += 1
        else:
            # "loose" : on tolère un espacement différent (fusion/duplication
            # d'espaces au décodage, fréquente avec les tokeniseurs SentencePiece).
            if " ".join(dec_n.split()) == " ".join(s.split()):
                exact_loose += 1
            else:
                # Round-trip raté sur autre chose qu'un espace : on diffe caractère
                # par caractère pour identifier PRÉCISÉMENT quels codepoints ont
                # disparu (typiquement un caractère sar devenu <unk> puis supprimé
                # au décodage). C'est ce diagnostic qui a permis d'identifier les
                # 4 caractères cassés par NLLB (voir docs/TOKENIZATION.md).
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
        # Nom Unicode inclus pour la lisibilité du rapport (ex. "U+1E2D LATIN SMALL
        # LETTER I WITH TILDE BELOW" plutôt qu'un codepoint nu).
        "lost_codepoints": {
            f"U+{ord(c):04X} {unicodedata.name(c, '?')}": cnt
            for c, cnt in lost.most_common(15)
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                     help="Identifiants Hugging Face des tokeniseurs à évaluer.")
    ap.add_argument("--sample", type=int, default=3000,
                     help="Nombre de phrases par langue (troncature déterministe, "
                          "voir le docstring du module).")
    ap.add_argument("--out", default=str(ROOT / "docs/TOKENIZATION_EVAL.md"),
                     help="Chemin du rapport Markdown généré.")
    args = ap.parse_args()

    try:
        import transformers
        from transformers import AutoTokenizer
    except ImportError as e:
        sys.exit(f"transformers requis (pip install -r requirements.txt) : {e}")

    print(f"transformers=={transformers.__version__}")  # utile pour reproduire les résultats

    corpus = load_corpus(args.sample)
    print(f"Corpus : {len(corpus['sar'])} phrases sar, {len(corpus['fr'])} phrases fr "
          f"(échantillon={args.sample})\n")

    report = collections.OrderedDict()
    for name in args.models:
        print(f"=== {name} ===")
        try:
            tok = AutoTokenizer.from_pretrained(name)
        except Exception as e:
            # On continue sur les autres modèles même si l'un d'eux échoue à charger
            # (pas de réseau, dépôt renommé, etc.) : le rapport le signale au lieu
            # d'interrompre toute l'évaluation.
            print(f"  ÉCHEC chargement : {e}\n")
            report[name] = {"error": str(e)}
            continue
        unk_id = getattr(tok, "unk_token_id", None)
        entry = {"vocab_size": tok.vocab_size, "unk_token": tok.unk_token}
        for lang in ("sar", "fr"):
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

    # --- Rapport Markdown : tableau comparatif + détail des pertes + JSON brut, pour
    # que le résultat soit à la fois lisible et ré-exploitable (analyse ultérieure,
    # figure de thèse) sans avoir à relancer l'évaluation. ---
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Évaluation des tokeniseurs sur le corpus sar\n",
             f"_Échantillon : {args.sample} phrases par langue. "
             f"Round-trip = decode(encode(x)) == x après normalisation NFC. "
             f"transformers=={transformers.__version__}._\n",
             "\n| Tokeniseur | Lang | Round-trip exact | Round-trip loose | Fertilité (tok/mot) | <unk>/1k | p95 longueur |",
             "|---|---|---|---|---|---|---|"]
    for name, e in report.items():
        if "error" in e:
            lines.append(f"| {name} | — | ERREUR | | | | |")
            continue
        for lang in ("sar", "fr"):
            r = e[lang]
            lines.append(f"| {name} | {lang} | {r['roundtrip_exact_%']}% | {r['roundtrip_loose_%']}% "
                         f"| {r['fertility_tok_per_word']} | {r['unk_per_1k_tokens']} | {r['len_p95']} |")
    lines.append("\n## Détail (codepoints perdus)\n")
    for name, e in report.items():
        if "error" in e:
            continue
        lines.append(f"### {name}")
        for lang in ("sar", "fr"):
            lost = e[lang]["lost_codepoints"]
            lines.append(f"- **{lang}** : {lost if lost else 'aucune perte'}")
    lines.append("\n## JSON complet\n\n```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    lines.append("```")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapport écrit : {out}")


if __name__ == "__main__":
    main()
