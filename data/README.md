# Données

Les données volumineuses et/ou sous droits **ne sont pas dans git**. Elles sont
versionnées avec [DVC](https://dvc.org) : git ne contient que les pointeurs
`data/*.dvc`, le contenu réel est stocké sur un *remote* DVC.

```
data/
├── raw.dvc              # sources brutes (PDF, corpus bruts) — voir licences ci-dessous
├── intermediate.dvc     # sorties intermédiaires d'extraction
├── processed.dvc        # corpus nettoyés / alignés / splits
├── annotation_ready.dvc # CSV chargés dans la plateforme DATA4CHAD
├── samples/             # petits extraits d'illustration du format (dans git)
└── README.md            # ce fichier
```

## Récupérer les données

```bash
pip install -r requirements-dev.txt      # installe dvc
dvc pull                                  # télécharge raw/ intermediate/ processed/ annotation_ready/
```

`dvc pull` nécessite l'accès au remote DVC (voir avec le mainteneur).
Un remote local par défaut (`localbackup`) est défini dans `.dvc/config.local`
(non versionné, propre à chaque machine). Pour un remote partagé :

```bash
dvc remote add -d shared <url>            # ex. gdrive://<folder-id>, s3://<bucket>/saar, ssh://…
dvc push
```

## Régénérer les données à partir des sources

Voir [`../docs/ROADMAP.md`](../docs/ROADMAP.md) (Phase 0) et les pipelines :

```bash
python -m scripts.dictionary.pipeline     # dictionnaire  -> paires FR-SAR
python -m scripts.bible.pipeline          # Bible SARDC    -> paires alignées
python -m scripts.sara_lexicon.extract    # lexique Sara   -> paires
python -m scripts.cosmogonie.process      # cosmogonie     -> phrases monolingues Sar
python -m scripts.tatoeba.fetch           # français       -> phrases (back-translation)
python -m scripts.build_corpus            # fusion + splits train/val
python -m scripts.prepare_annotation      # -> data/annotation_ready/*.csv
```

## Sources et licences

| Source | Contenu | Licence / statut | Redistribuable ? |
|---|---|---|---|
| **Bible SARDC** | ~32 000 versets Sar + FR (Louis Segond) | © Alliance Biblique du Tchad, 2006/2010 | ❌ Non — autorisation requise |
| **Dictionnaire Sar** | Keegan & Gotengaye — ~3 200 entrées | à clarifier avec les auteurs | ❌ Non pour l'instant |
| **Cosmogonie Sar** | texte rituel, © OSSEC 2015 | autorisation ayants droit requise | ❌ Non |
| **Sara Languages Lexicon** | Keegan, Sara-Bagirmi Language Project | à vérifier (projet publié ouvertement) | ⚠️ À confirmer |
| **Tatoeba (français)** | ~100 000 phrases | CC-BY 2.0 FR | ✅ Oui, avec attribution |

**Règle : seuls les modèles entraînés et les données 100 % originales
(annotations produites via DATA4CHAD) sont publiables librement.**
Provenance détaillée : [`../docs/SOURCES.md`](../docs/SOURCES.md)
(*datasheet* formelle à produire — cf. ROADMAP Phase 0).
