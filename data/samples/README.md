# data/samples/

Ce répertoire présente les exemples du format des données, un dossier par source. Le corpus complet n'est pas partagé ici, il est suivi par DVC et reste privé pour le moment.

`tatoeba/` est le seul dossier avec du contenu réel : Tatoeba est en CC-BY,
donc redistribuable avec attribution. `example.jsonl` reprend 5 phrases telles
quelles depuis `data/processed/tatoeba/fra_filtered.jsonl`.

`dictionary/`, `bible/`, `cosmogonie/` et `sara_lexicon/` sont vides; ces
quatre sources ne sont pas encore autorisées à la redistribution.

Format des paires bilingues (`data/processed/sar_fr_all_pairs.jsonl`), une
ligne JSON par paire :

```json
{"sar": "...", "fr": "...", "source": "bible"}
```

Le monolingue sar (`data/processed/sar_monolingual.txt`) est juste une phrase
par ligne, sans métadonnées.
