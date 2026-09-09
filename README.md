# sar-nlp

**sar-nlp** réunit des données textuelles — un corpus parallèle sar–français et un
corpus sar monolingue — et des outils de traitement automatique des langues (TAL) pour
le **sar**, une langue sara du Moyen-Chari, au sud du Tchad
(ISO 639-3 [`sar`](https://iso639-3.sil.org/code/sar)). Ce dépôt sert de support à une
proposition de projet de thèse.

Le sar est très peu doté pour le TAL. Les sources écrites exploitables sont rares (une
bible, un dictionnaire, quelques textes traditionnels), la langue est absente des
grands modèles multilingues — dont les 200 langues de NLLB-200 —, et les tokeniseurs
courants dégradent son orthographe latine, dense en tons et en voyelles nasales
(voir [tokenisation](#ce-que-lanalyse-de-tokenisation-a-montré)). Le projet part de ces
sources pour construire, étape par étape, un corpus propre puis des modèles de
traduction et de langue utilisables, en produisant au passage les outils qui manquent.

Le dépôt contient le volet recherche : construction du corpus, analyse linguistique,
tokenisation, modèles. La plateforme d'annotation qui l'alimente vit dans deux dépôts
séparés (voir [Organisation](#organisation)).

## Où en est le corpus — septembre 2026

12 717 paires sar–français : 8 726 issues de la Bible, 3 193 du dictionnaire, 798 d'un
lexique sara. Après retrait des doublons, environ 12 450 phrases sar distinctes.
S'ajoutent 26 389 lignes de sar monolingue (~342 000 mots) et 100 000 phrases
françaises de Tatoeba pour la rétro-traduction. Le vocabulaire sar observé compte
~11 400 formes, dont 739 hapax ; les 2 000 formes les plus fréquentes couvrent 93 %
des occurrences.

Deux limites orientent tout le travail qui suit. Le corpus est petit — à cette échelle,
NLLB classe une paire de langues en « très faibles ressources ». Et il est à ~80 % de
registre biblique : élargir les domaines (langue courante, santé, agriculture, presse)
est la priorité qui traverse la feuille de route.

Les données ne sont pas dans git, pour des raisons de droits et de volume — voir
[Données et licences](#données-et-licences).

## Ce que l'analyse de tokenisation a montré

Avant d'entraîner quoi que ce soit, j'ai mesuré comment les tokeniseurs pré-entraînés
se comportent sur le sar
([`scripts/eval_tokenizers.py`](scripts/eval_tokenizers.py) ;
rapport complet dans [`docs/TOKENIZATION.md`](docs/TOKENIZATION.md)) :

| Tokeniseur | Aller-retour exact (sar) | Fertilité (tokens/mot) | `<unk>` / 1 000 tokens |
|---|---|---|---|
| NLLB-200-distilled-600M | 74 % | 2,43 (français : 1,6) | 8,3 |
| mT5-base | 94 % | 3,06 | 1,4 |
| ByT5 (niveau octet) | 100 % | 6,22 | 0 |
| XLM-R / mBART-50 / AfroXLM-R | 55 % | 2,85 | 14,2 |

Aucun tokeniseur existant ne traite le sar sans perte. NLLB — le meilleur des quatre,
et la cible du fine-tuning — supprime silencieusement quatre caractères (`ḭ ḛ ṵ ȳ`,
des voyelles nasales et un ton bas) : 27 % des phrases contiennent alors au moins un
`<unk>` irréversible. La conclusion pour la thèse est d'étendre le tokeniseur de NLLB
(caractères manquants, sous-mots sar, jeton de langue `sar_Latn`) avant tout
entraînement, plutôt que de le prendre tel quel.

## Le plan

0. **Socle de données** *(en cours)* — un corpus canonique unique, normalisé
   (Unicode NFC, encodage homogène de la nasalité), avec des découpes train/dev/test
   gelées et sans fuite d'un ensemble à l'autre.
1. **Tokenisation** — tokeniseur NLLB étendu, aller-retour sans perte, figé.
2. **Première traduction** — NLLB-200-distilled-600M affiné en LoRA, sar↔français,
   évalué en chrF++ et par un locuteur, publié sur le Hub Hugging Face.
3. **Agrandir le corpus** — boucle « suggestion machine → correction humaine » sur la
   plateforme, plus rétro-traduction, pour viser 30 000 puis 50 000 paires et faire
   baisser la part biblique.
4. **Modèle de langue sar** — adaptation d'un encodeur sur le sar monolingue.
5. **Outils** — correcteur orthographique, étiquetage morphosyntaxique, reconnaissance
   et synthèse vocale, dictionnaire numérique.

Les entraînements se font sur Colab / Kaggle gratuit : LoRA en 4 bits, reprises après
interruption, pas de pré-entraînement à partir de zéro. Détail des critères de passage
d'une étape à l'autre dans [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Organisation

Trois dépôts, sans dépendances de code entre eux, avec des contraintes de licence et
des déploiements distincts :

| Dépôt | Rôle | Pile |
|---|---|---|
| **`sar-nlp`** (ici) | recherche : corpus, tokenisation, modèles, évaluation | Python |
| [`khalima-backend`](https://github.com/Titembaye/khalima-backend) | API de la plateforme d'annotation DATA4CHAD | Django, PostgreSQL |
| [`khalima-frontend`](https://github.com/Titembaye/khalima-frontend) | interface d'annotation (phrase/mot, bidirectionnelle, clavier sar) | React, Vite |

La plateforme DATA4CHAD ([data4chad.vercel.app](https://data4chad.vercel.app)) sert à
collecter et corriger les traductions à la main ; ses exports alimentent
`data/annotation_ready/`.

```
sar-nlp/
├── scripts/          extraction des sources, construction du corpus, tokenisation
├── notebooks/        finetune_nllb_sar.ipynb  — fine-tuning NLLB-200 + LoRA (brouillon)
├── docs/             ROADMAP, TOKENIZATION, ENCODING (orthographe sar), SOURCES
├── data/             suivi par DVC — voir data/README.md
└── config.json       sources, schéma de sortie, filtres de qualité
```

## Données et licences

Les gros fichiers et les sources sous droits sont versionnés avec
[DVC](https://dvc.org) : git ne garde que les pointeurs `data/*.dvc`.

```bash
pip install -r requirements-dev.txt
dvc pull        # accès au remote à demander au mainteneur
```

Le code est sous licence MIT ([`LICENSE`](LICENSE)). Les données ne le sont pas et
gardent leurs conditions propres :

- **Bible SARDC** — © Alliance Biblique du Tchad, 2006/2010, non redistribuable
- **Dictionnaire sar** — licence à clarifier avec les auteurs
- **Cosmogonie** — © OSSEC 2015, autorisation requise
- **Tatoeba (français)** — CC-BY 2.0 FR, redistribuable avec attribution

Seuls les modèles entraînés et les données produites via DATA4CHAD peuvent être
diffusés librement. Provenance détaillée dans [`docs/SOURCES.md`](docs/SOURCES.md).

## Mise en route

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt                    # requirements-dev.txt pour DVC
```

Python 3.12+. Reconstruire le corpus depuis les sources :

```bash
python -m scripts.dictionary.pipeline
python -m scripts.bible.pipeline
python -m scripts.sara_lexicon.extract
python -m scripts.cosmogonie.process
python -m scripts.tatoeba.fetch
python -m scripts.build_corpus            # fusion + découpes train/val
python -m scripts.prepare_annotation      # exports pour la plateforme
```

Rejouer l'évaluation des tokeniseurs : `python -m scripts.eval_tokenizers --sample 3000`.

## Citer ce travail

Voir [`CITATION.cff`](CITATION.cff).
