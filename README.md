# sar-nlp

> Corpus parallèle et outils de traitement automatique des langues (TAL) pour le
> **sar** — langue sara parlée dans la région du Moyen-Chari, au Tchad
> (ISO 639-3 [`sar`](https://iso639-3.sil.org/code/sar)).

Travaux de thèse en cours. Ce dépôt contient le **cœur de recherche** : construction
du corpus, analyse linguistique, tokenisation, modèles. La plateforme d'annotation
qui alimente le corpus vit dans deux dépôts séparés (voir [Structure](#structure-du-projet)).

📍 **Feuille de route détaillée : [`docs/ROADMAP.md`](docs/ROADMAP.md)**

---

## Contexte et objectif

Le sar est une langue **à très faibles ressources** : pas de corpus TAL public, pas de
présence dans les modèles multilingues courants (absente des 200 langues de NLLB-200),
écriture latine étendue riche en diacritiques (tons, nasalité) mal gérée par les
tokeniseurs existants.

**Objectif de la thèse :** valoriser le sar par le TAL, de façon incrémentale —
d'un corpus parallèle propre jusqu'à la traduction automatique et des modèles de langue
réutilisables, en construisant en parallèle les outils et les données qui manquent.

**Principe directeur :** le goulot n'est pas le modèle, c'est le corpus. Chaque étape
doit soit augmenter la quantité / qualité / diversité des données, soit rendre l'étape
suivante possible.

## État du corpus — 2026-09

| Ressource | Volume | Note |
|---|---|---|
| Paires sar ↔ français | **12 717** | 8 726 Bible · 3 193 dictionnaire · 798 lexique sara |
| Phrases sar distinctes | ~12 452 | 104 doublons exacts, 812 entrées de 1-2 mots |
| Monolingue sar | 26 389 lignes / ~342 k mots | Bible, cosmogonie, exemples du dictionnaire |
| Vocabulaire sar | ~11 400 formes | 739 hapax ; les 2 000 formes les plus fréquentes couvrent 93 % |
| Français monolingue (Tatoeba) | 100 000 phrases | pour la *back-translation* |

- Longueur médiane : 13 mots (sar) / 16 mots (fr).
- **Biais principal : ~80 % du bilingue est de registre biblique.** Diversifier les
  domaines (langue courante, santé, agriculture, presse) est une priorité transversale.
- Les données ne sont **pas** dans git (droits + volume) — voir [Données](#données).

## Résultat préliminaire — tokenisation

Évaluation de tokeniseurs pré-entraînés sur le corpus sar
([`scripts/eval_tokenizers.py`](scripts/eval_tokenizers.py),
rapport : [`docs/TOKENIZATION.md`](docs/TOKENIZATION.md)) :

| Tokeniseur | Aller-retour exact (sar) | Fertilité (tok/mot) | `<unk>` / 1k |
|---|---|---|---|
| NLLB-200-distilled-600M | 74 % | 2,43 (fr : 1,6) | 8,3 |
| mT5-base | 94 % | 3,06 | 1,4 |
| ByT5 (octets) | 100 % | 6,22 | 0 |
| XLM-R / mBART-50 / AfroXLM-R | 55 % | 2,85 | 14,2 |

**Aucun tokeniseur existant ne gère le sar sans perte.** NLLB (le meilleur, et la cible
du *fine-tuning*) détruit silencieusement 4 caractères (`ḭ ḛ ṵ ȳ` — voyelles nasales et
ton bas) : 27 % des phrases contiennent au moins un `<unk>` irréversible.
→ Décision : **étendre le tokeniseur NLLB** (caractères manquants + sous-mots sar +
token de langue `sar_Latn`) avant tout entraînement.

## Feuille de route

| Phase | Objectif | Statut |
|---|---|---|
| **0 — Socle de données** | corpus canonique unique, normalisé (Unicode NFC + nasalité), splits gelés sans fuite | en cours |
| **1 — Tokenisation** | tokeniseur NLLB étendu, aller-retour 100 %, gelé v1 | à faire |
| **2 — Baseline de traduction** | NLLB-200-distilled-600M + LoRA, sar↔fr, évalué (chrF++, éval humaine), publié | à faire |
| **3 — Agrandissement du corpus** | boucle suggestion machine → correction humaine + *back-translation* ; 12k → 30k → 50k paires | à faire |
| **4 — Modèle de langue sar** | *continued pretraining* d'un encodeur sur le monolingue | à faire |
| **5 — Outils** | correcteur orthographique, POS, ASR/TTS, dictionnaire numérique | à faire |

Contrainte matérielle : entraînements sur **Colab / Kaggle gratuit** → LoRA 4-bit,
checkpoints reprenables, pas de pré-entraînement *from scratch*.

## Structure du projet

Trois dépôts séparés (pas de monorepo — code sans dépendances croisées, contraintes de
licence différentes, déploiements indépendants) :

| Dépôt | Rôle | Stack |
|---|---|---|
| **`sar-nlp`** (ici) | recherche : corpus, tokenisation, modèles, évaluation | Python |
| [`khalima-backend`](https://github.com/Titembaye/khalima-backend) | API de la plateforme d'annotation **DATA4CHAD** | Django + PostgreSQL |
| [`khalima-frontend`](https://github.com/Titembaye/khalima-frontend) | interface d'annotation (multi-granularité, bidirectionnelle, clavier sar) | React / Vite |

DATA4CHAD ([data4chad.vercel.app](https://data4chad.vercel.app)) sert à collecter et
corriger les traductions à la main ; ses CSV alimentent `data/annotation_ready/` de ce dépôt.

```
sar-nlp/
├── scripts/
│   ├── dictionary/     extraction du dictionnaire sar (PDF → paires FR-SAR)
│   ├── bible/          alignement Bible SARDC ↔ français
│   ├── sara_lexicon/   extraction du lexique multilingue sara
│   ├── cosmogonie/     extraction du texte de cosmogonie (monolingue sar)
│   ├── tatoeba/        récupération de phrases françaises
│   ├── build_corpus.py     fusion + splits train/val
│   ├── prepare_annotation.py  export vers la plateforme
│   ├── tokenize.py         entraînement/application SentencePiece
│   └── eval_tokenizers.py  évaluation de tokeniseurs sur le corpus sar
├── notebooks/
│   └── finetune_nllb_sar.ipynb   fine-tuning NLLB-200 + LoRA (brouillon)
├── docs/
│   ├── ROADMAP.md      feuille de route (6 phases, critères de sortie)
│   ├── TOKENIZATION.md diagnostic + décision tokenisation
│   ├── ENCODING.md     spécification d'encodage du sar (alphabet, tons, NFC)
│   └── SOURCES.md      provenance et licences des sources
├── data/              suivi par DVC — voir data/README.md
├── config.json        configuration du corpus (sources, schéma, filtres)
└── requirements.txt
```

## Données

Les données volumineuses et/ou sous droits sont versionnées avec [DVC](https://dvc.org),
pas dans git : git ne contient que les pointeurs `data/*.dvc`.

```bash
pip install -r requirements-dev.txt   # installe dvc
dvc pull                              # nécessite l'accès au remote (voir mainteneur)
```

**Licences** — seuls les modèles entraînés et les données 100 % originales (annotations
produites via DATA4CHAD) sont publiables librement. Détails :
[`data/README.md`](data/README.md) et [`docs/SOURCES.md`](docs/SOURCES.md).

| Source | Licence | Redistribuable |
|---|---|---|
| Bible SARDC | © Alliance Biblique du Tchad, 2006/2010 | ❌ |
| Dictionnaire sar | à clarifier avec les auteurs | ❌ |
| Cosmogonie | © OSSEC 2015 | ❌ |
| Tatoeba (français) | CC-BY 2.0 FR | ✅ avec attribution |

## Installation

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt                    # + requirements-dev.txt pour DVC
```

Python 3.12+. L'entraînement des modèles (torch, peft, datasets) se fait sur Colab/Kaggle,
voir `notebooks/`.

## Construction du corpus

```bash
python -m scripts.dictionary.pipeline     # dictionnaire  → paires FR-SAR
python -m scripts.bible.pipeline          # Bible SARDC    → paires alignées
python -m scripts.sara_lexicon.extract    # lexique sara   → paires
python -m scripts.cosmogonie.process      # cosmogonie     → phrases monolingues
python -m scripts.tatoeba.fetch           # français       → phrases
python -m scripts.build_corpus            # fusion + splits train/val
python -m scripts.prepare_annotation      # → data/annotation_ready/*.csv
```

## Évaluation de la tokenisation

```bash
python -m scripts.eval_tokenizers --sample 3000
# → docs/TOKENIZATION_EVAL.md
```

## Licence et citation

Code sous licence **MIT** ([`LICENSE`](LICENSE)) — les données ne sont **pas** couvertes
et conservent leurs termes propres. Pour citer ces travaux, voir
[`CITATION.cff`](CITATION.cff).

## Statut

Projet de recherche à un stade précoce. Le corpus est petit et biaisé vers le registre
biblique ; les résultats de tokenisation sont préliminaires ; aucun modèle de traduction
n'a encore été entraîné. La feuille de route décrit le plan pour lever ces limites.
