# data/samples/

Exemples du format des données, un dossier par source (mêmes noms que dans
`scripts/`). Le corpus complet n'est pas ici — il est suivi par DVC, voir
`data/README.md` pour le récupérer et pour le détail des licences.

`tatoeba/` est le seul dossier avec du contenu réel : Tatoeba est en CC-BY,
donc redistribuable avec attribution. `example.jsonl` reprend 5 phrases telles
quelles depuis `data/processed/tatoeba/fra_filtered.jsonl`.

`dictionary/`, `bible/`, `cosmogonie/` et `sara_lexicon/` sont vides — ces
quatre sources ne sont pas (encore) autorisées à la redistribution. Chaque
dossier contient juste une note qui le rappelle.

Format des paires bilingues (`data/processed/sar_fr_all_pairs.jsonl`), une
ligne JSON par paire :

```json
{"sar": "...", "fr": "...", "source": "bible"}
```

Le monolingue sar (`data/processed/sar_monolingual.txt`) est juste une phrase
par ligne, sans métadonnées.
