# sar-nlp

Ce dépôt rassemble le corpus, le code et les premiers résultats d'une proposition de thèse de doctorat sur la **tokenisation morphologique et tonale** du **sar**, une langue sara du Moyen-Chari et du Mandoul, au sud du Tchad
(ISO 639-3 [`mwm`](https://iso639-3.sil.org/code/mwm)).

Les tokeniseurs statistiques (BPE, WordPiece, SentencePiece) construisent leur
vocabulaire en optimisant la fréquence des sous-chaînes de caractères, sans aucune
connaissance de la morphologie ni de la phonologie de la langue. En sar, où une même
voyelle porte à la fois le timbre, la nasalité et le ton, ce découpage produit des
unités linguistiquement incohérentes - et, avec les tokeniseurs pré-entraînés, détruit
de l'information. La thèse propose de concevoir, valider et évaluer une méthode de
tokenisation qui sépare et représente explicitement ces couches, puis d'en tester la
généralisation à une autre langue sara-baguirmienne. La proposition du projet de thèse complet est disponible dans: [`docs/projet_these.pdf`](docs/projet_these.pdf).


## Premiers Tests

Afin de mesurer l'impact des tokeniseurs pré-entraînés sur le sar, nous avons évalué
leur comportement avec [`scripts/eval_tokenizers.py`](scripts/eval_tokenizers.py)
(méthodologie, limites et reproductibilité documentées dans les commentaires du
script). Résultats sur un échantillon de 3 000 phrases :

| Tokeniseur | Aller-retour exact (sar) | Fertilité (tokens/mot) | `<unk>` / 1 000 tokens |
|---|---|---|---|
| NLLB-200-distilled-600M | 74 % | 2,43 (français : 1,6) | 8,3 |
| mT5-base | 94 % | 3,06 | 1,4 |
| ByT5 (niveau octet) | 100 % | 6,22 | 0 |
| XLM-R / mBART-50 / AfroXLM-R | 55 % | 2,85 | 14,2 |

Aucun tokeniseur pré-entraîné ne traite le sar sans perte : NLLB, le meilleur des
quatre, supprime silencieusement quatre caractères (`ḭ ḛ ṵ ȳ` — voyelles nasales et
ton bas), et 27 % des phrases contiennent alors au moins un `<unk>` irréversible. Le
sar est aussi fragmenté 2,4 fois plus que le français par le même modèle.

Ces chiffres **confirment et quantifient le problème** posé par la thèse ; ils ne
valident encore aucune méthode. Ils portent sur des tokeniseurs *transférés* : un BPE
entraîné directement sur le corpus sar n'aurait pas de `<unk>`, mais la fragmentation
et l'incohérence des frontières — ce que la méthode proposée doit corriger — restent
entières.

Sous-résultat pour la question des conventions orthographiques : la nasalité est
encodée de **deux façons incohérentes** dans le corpus actuel — voyelles précomposées
(`ḭ ḛ ṵ`) d'un côté, base + diacritique combinant (`a̰ o̰ ə̰`) de l'autre. À homogénéiser
et à faire confirmer par un locuteur ou une source de référence.

## Où en est le corpus — septembre 2026

12 717 paires sar–français : 8 726 issues de la Bible, 3 193 du dictionnaire, 798 d'un
lexique sara ; environ 12 450 phrases sar distinctes après retrait des doublons.
S'ajoutent 26 389 lignes de sar monolingue (~342 000 mots). Le vocabulaire sar observé
compte ~11 400 formes, dont 739 hapax ; les 2 000 plus fréquentes couvrent 93 % des
occurrences. 100 000 phrases françaises (Tatoeba) sont disponibles comme corpus de
comparaison.

Le corpus est encore petit et à ~80 % de registre biblique — deux limites que le
premier lot de travail vise directement. Les données ne sont pas dans git (droits,
volume) : voir [Données et licences](#données-et-licences).

## Prochaines étapes

Les lots de travail de la thèse (détail dans le PDF) :

1. **Corpus** — l'étendre au-delà des textes bibliques et de la cosmogonie déjà
   rassemblés ; faire confirmer les conventions de notation des tons par un locuteur ou
   une source de référence ; annotation de validation sur échantillon, avec la
   traduction française des unités lexicales.
2. **Méthode** — séparer les couches phonologiques du sar (voyelle, nasalité, ton) en
   flux de tokens distincts, sur le modèle du précédent mixtèque de Yoloxóchitl, et
   intégrer une contrainte morphologique aux fusions.
3. **Évaluation** — comparer la méthode à BPE et WordPiece sur le corpus sar : entropie
   de Rényi de la distribution des tokens, taille de vocabulaire à couverture donnée,
   au moins une tâche aval (classification ou étiquetage).
4. **Généralisation** — appliquer la méthode à une seconde langue sara-baguirmienne
   (probablement le ngambay), avec les mêmes critères.
5. **Validation appliquée** — prototype de reconnaissance vocale sur un vocabulaire
   médical restreint, pour des zones où le français n'est pas la langue du quotidien.

## Organisation

Trois dépôts, sans dépendances de code entre eux :

| Dépôt | Rôle | Pile |
|---|---|---|
| **`sar-nlp`** (ici) | corpus, extraction, analyse de tokenisation, expériences | Python |
| [`khalima-backend`](https://github.com/Titembaye/khalima-backend) | API de la plateforme d'annotation DATA4CHAD (lot 1) | Django, PostgreSQL |
| [`khalima-frontend`](https://github.com/Titembaye/khalima-frontend) | interface d'annotation (phrase/mot, bidirectionnelle, clavier sar) | React, Vite |

La plateforme DATA4CHAD ([data4chad.vercel.app](https://data4chad.vercel.app)) sert à
l'annotation et à la validation par des locuteurs ; ses exports alimentent
`data/annotation_ready/`.

```
sar-nlp/
├── scripts/          extraction des sources, construction du corpus, tokenisation
├── docs/             projet de thèse (PDF)
└── data/             suivi par DVC — voir data/README.md
```

## Données et licences

Les gros fichiers et les sources sous droits sont versionnés avec
[DVC](https://dvc.org) : git ne garde que les pointeurs `data/*.dvc`.

```bash
pip install -r requirements-dev.txt
dvc pull        # accès au remote à demander au mainteneur
```

Le code est sous licence MIT ([`LICENSE`](LICENSE)). Les données gardent leurs
conditions propres :

- **Bible SARDC** — © Alliance Biblique du Tchad, 2006/2010, non redistribuable
  (demande d'autorisation en cours)
- **Dictionnaire sar** — licence à clarifier avec les auteurs
- **Cosmogonie** — © OSSEC 2015, autorisation requise
- **Tatoeba (français)** — CC-BY 2.0 FR, redistribuable avec attribution

Seuls les modèles et outils produits, et les données créées via DATA4CHAD, pourront
être diffusés librement.

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
python -m scripts.build_corpus            # fusion + découpes
python -m scripts.prepare_annotation      # exports pour la plateforme
```

Rejouer l'analyse des tokeniseurs : `python -m scripts.eval_tokenizers --sample 3000`.

## Citer ce travail

Voir [`CITATION.cff`](CITATION.cff).
