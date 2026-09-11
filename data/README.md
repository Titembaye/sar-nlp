# Données

Les données volumineuses et/ou sous droits **ne sont pas dans git**. Elles sont
versionnées avec [DVC](https://dvc.org).

```
data/
├── raw.dvc              # sources brutes (PDF, corpus bruts)
├── intermediate.dvc     # sorties intermédiaires d'extraction
├── processed.dvc        # corpus nettoyés / alignés / splits
├── annotation_ready.dvc # CSV chargés dans la plateforme pour faire de l'annotation
├── samples/             # petits extraits d'illustration du format (dans git)
└── README.md            # ce fichier
```

## Sources et licences

| Source | Contenu | Licence / statut |
|---|---|---|
| **Bible SARDC** | ~32 000 versets Sar + FR (Louis Segond) | © Alliance Biblique du Tchad, 2006/2010 |
| **Dictionnaire Sar** | Keegan & Gotengaye — ~3 200 entrées | à clarifier avec les auteurs |
| **Cosmogonie Sar** | texte rituel, © OSSEC 2015 | autorisation des ayants droit requise |
| **Sara Languages Lexicon** | Keegan, Sara-Bagirmi Language Project | à vérifier (projet publié ouvertement) |
| **Tatoeba (français)** | ~100 000 phrases | CC-BY 2.0 FR |

La question de la distribution des données sera tranchée à l'avenir. Sauf Tatoeba
(déjà en CC-BY, donc redistribuable avec attribution), les ensembles de données
que nous exploitons ici restent privés tant qu'une autorisation explicite n'a pas
été obtenue.
