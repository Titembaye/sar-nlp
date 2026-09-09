# data/samples/

Petits extraits pour illustrer le **format** des données, sans redistribuer les
corpus sous droits. Contenu volontairement minimal.

> **À faire** : ajouter ici `sample_pairs.jsonl` avec ~15 exemples **libres de droits**
> (phrases construites par le mainteneur, ou extraits Tatoeba CC-BY côté français).
> Ne pas y copier de versets SARDC ni d'entrées du dictionnaire.

## Schéma des paires (`sample_pairs.jsonl`)

Un objet JSON par ligne :

| Champ | Type | Description |
|---|---|---|
| `sar` | string | Phrase en sar, normalisée NFC |
| `fr` | string | Traduction française |
| `source` | string | `bible` \| `dictionary` \| `sara_lexicon` \| `cosmogonie` \| `annotation` |

```json
{"sar": "…", "fr": "…", "source": "dictionary"}
```

## Schéma monolingue (`data/processed/sar_monolingual.txt`)

Une phrase sar par ligne, NFC, sans métadonnées.

## Note

Le corpus complet (~12 700 paires + ~26 000 phrases monolingues) est suivi par
DVC et non redistribué. Voir [`../README.md`](../README.md).
