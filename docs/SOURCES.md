# Documentation des Sources

## 1. Bible Saar (SARDC)

### Informations Générales
- **Code langue ISO 639-3** : `sar`
- **Nom complet** : Saar Bible (SARDC - Sara Dunjo Reference Collection)
- **Source** : https://www.bible.com/fr/bible/445
- **Couverture** : Bible complète (Ancien + Nouveau Testament)
- **Nombre de versets** : ~32,000

### Format Actuel
**Fichier** : `data/raw/sardc_bible.jsonl`  
**Une ligne par verset (JSONL)** :
```json
{"ref": "GEN.1.1", "book": "GEN", "chapter": 1, "verse": 1, "text": "Ta kəga dɔ sasak Nə́ɓā əndā dɔ rā̰ ō, dɔ nang ō."}
```

### Extraction
- **Script** : `scripts/extract_bible.py` (déjà présent)
- **Méthode** : Web scraping avec Playwright (rendering JS)
- **Délai** : 1 sec entre requêtes (respect du serveur)
- **Reprise** : Détecte les versets déjà collectés (no duplicate)

### Points Clés
✅ Données structurées (ref, chapitre, verset)  
✅ Alignement potentiel avec traductions FR (Bible FR sur Bible.com)  
⚠️ Couverture biblique complète (peut avoir redondances thématiques)  
⚠️ Limitation : uniquement versets, pas de commentaires

### Utilisation ML
- **Traduction directe** : Versets FR standard vs Saar
- **Similarité sémantique** : Même verset à travers livres bibliques
- **Augmentation de données** : Paraphrases bibliques

---

## 2. Cosmogonie Saar

### Informations Générales
- **Titre original** : "Ta ra dora̰ kə donang" (La cosmogonie Saar)
- **Source** : PDF 2015 © OSSEC (Organisation Sara pour la Science, l'Education et la Culture)
- **Type** : Texte rituel / Mythologie traditionnelle
- **Pages** : ~50 pages de texte continu

### Format Actuel
**Fichier** : `data/raw/cosmogonie_sar.txt`  
**Extraction de PDF** : Via PyMuPDF avec filtres personnalisés

### Filtrage Appliqué
Le script `extract_cosmogonie_sar.py` :
- ✅ Garde texte Saar (caractères diacritiques)
- ❌ Élimine blocs français pur (introduction, commentaires)
- ❌ Élimine tables des matières, numérotation
- ❌ Élimine titres de sections standardisés

### Points Clés
✅ Texte authentique en Saar (pas traduction)  
✅ Contexte rituel/culturel riche  
✅ Nettoyage linguistique automatisé  
⚠️ Pas d'alignement FR-SAR directe (texte primaire Saar)  
⚠️ Structure paragraphe (pas de versification)

### Utilisation ML
- **Langue naturelle** : Proses complexes (vs versets bibliques simples)
- **Reconnaissance d'entités** : Noms propres, personnages mythologiques
- **Augmentation de données** : Diversité stylistique
- **Morphologie** : Structures grammaticales plus élaborées

---

## 3. Dictionnaire Saar (Extraction en cours)

### Informations Générales
- **Format source** : PDF
- **Contenu supposé** : Entrées lexicales SAR → FR
- **Taille estimée** : 3,000 - 5,000 entrées
- **Localisation** : `data/raw/sar_dictionary.pdf`

### Extraction
- **Script** : `scripts/extract_dictionary.py`
- **Sorties** :
  - `data/raw/sar_dictionary_raw.txt` — texte brut extrait du PDF
  - `data/processed/sar_dictionary_entries.jsonl` — candidats d'entrées
- **Approche** : extraction PyMuPDF + heuristiques de parsing
- **Validation** : vérifier que le PDF contient du texte, sinon prévoir OCR

### Actions Requises
- [x] Localiser le fichier PDF
- [ ] Vérifier si le PDF est textuel ou scanné
- [ ] Ajuster l'analyse en fonction de la structure du dictionnaire
- [ ] Mapper SAR ↔ FR
- [ ] Normaliser Unicode

### Format Visé (Hypothétique)
```json
{
  "entry_id": "sar_001",
  "saar_word": "Nə́ɓā",
  "part_of_speech": "noun",
  "french_translation": "Dieu",
  "definition_saar": "[texte définition]",
  "example_saar": "Ta kəga dɔ sasak Nə́ɓā",
  "example_french": "Au commencement Dieu",
  "phonetic": "[nə́ɓa]",
  "notes": "Cosmologie religieuse"
}
```

### Utilisation ML
- **Traduction** : Alignements lexicaux directs
- **Word embeddings** : Vectors pour tokens Saar
- **Lemmatization** : Base lexicale pour dérivatifs
- **Augmentation** : Paraphrases basées sur définitions

---

## Consolidation et Alignment

### Stratégie FR ↔ SAR

1. **Bible** :
   - Versets bibliques français standards (BFC, Segond, etc.)
   - Mapper avec SARDC versets
   - Extraction automatique des paires alignées

2. **Cosmogonie** :
   - Pas d'équivalent FR direct dans source
   - Option : Traduction manuelle sélective (passages clés)
   - Alternative : Utiliser comme corpus monolingue Saar

3. **Dictionnaire** :
   - Alignement intrinsèque SAR → FR
   - Fusion avec contextes Bible/Cosmogonie

### Pipeline de Consolidation

```
Bible (SARDC + FR) 
    ↓ [Extraction paires]
    ├→ aligned_pairs.jsonl
    │
Cosmogonie (Saar seul)
    ↓ [Lemmatization]
    ├→ lexicon_saar.jsonl
    │
Dictionnaire (SAR ↔ FR)
    ↓ [Extraction mappings]
    ├→ dictionary_mappings.jsonl
    │
[FUSION]
    ↓
corpus_complet.jsonl
```

---

## Qualité et Nettoyage

### Nettoyage Recommandé

| Aspect | Action |
|--------|--------|
| Encodage | Normaliser Unicode NFC |
| Espaces | Trim, normaliser whitespace |
| Ponctuation | Préserver, mais documenter |
| Caractères mal OCR'd | Corriger (si PDF mal extrait) |
| Doublets | Détecter et merger |

### Validation

```python
import json
from collections import Counter

def validate_corpus(jsonl_file):
    """Vérifie intégrité du corpus."""
    with open(jsonl_file, encoding='utf-8') as f:
        entries = [json.loads(line) for line in f]
    
    print(f"Total entries: {len(entries)}")
    print(f"Unique sources: {Counter(e['source'] for e in entries)}")
    print(f"Avg text length: {sum(len(e['saar'].split()) for e in entries) / len(entries):.1f} tokens")
```

---

## Références et Licences

- Bible SARDC © Alliance Biblique du Tchad, 2006, 2010
- Cosmogonie © OSSEC, 2015
- Dictionnaire : [À clarifier avec source]
- Pipeline d'extraction : [auteur du projet]

## Contacts Utiles

- OSSEC : Organisation Sara pour la Science, l'Education et la Culture
- Bible.com : https://www.bible.com/fr/bible/445
- Communauté Saar : [À identifier]
