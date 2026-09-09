# Spécification d'Encodage Saar

## Alphabet et Caractères

### Consonnes
- **p, b** : occlusives bilabiales
- **t, d** : occlusives alvéolaires  
- **k, g** : occlusives vélaires
- **ɓ** : occlusive bilabiale implosive (U+0253)
- **ɗ** : occlusive alvéolaire implosive (U+0257)
- **f, v** : fricatives labio-dentales
- **s, z** : fricatives alvéolaires
- **ʃ, ʒ** : fricatives postalvéolaires
- **m, n** : nasales
- **l, r** : liquides
- **w, j** : semi-voyelles

### Voyelles
- **a, e, i, o, u** : voyelles simples
- **ə** : schwa (U+0259)
- **ɔ** : o ouvert (U+0254)
- **ɛ** : e ouvert (U+025B)

### Tons et Marques Diacritiques

| Signe | Unicode | Description | Exemple |
|-------|---------|-------------|---------|
| `̄` | U+0304 | Macron (ton haut) | `ā`, `ē` |
| `̰` | U+0330 | Tilde sous (ton bas/creaky) | `ā̰`, `ḛ̃` |
| `́` | U+0301 | Accent aigu (ton montant) | `á`, `é` |
| `̀` | U+0300 | Accent grave (ton descendant) | `à`, `è` |
| `̂` | U+0302 | Accent circonflexe | `â`, `ê` |

### Exemples Complexes
- `Nə́ɓā` : Dieu (schwa + ton montant + implosive bilabiale + ton haut)
- `ā̰` : ton bas/creaky (macron + tilde sous)
- `kə́` : tonalité montante

## Normalisation Unicode

**Standard à utiliser** : **NFC (Canonical Decomposition, followed by Canonical Composition)**

### Raison
- Assure la représentation cohérente des caractères avec diacritiques
- Évite les problèmes d'alignement lors du traitement NLP
- Facilite la comparaison de chaînes

### Implémentation Python

```python
import unicodedata

def normalize_saar(text):
    return unicodedata.normalize('NFC', text)

# Exemple
text = "Nə́ɓā əndā dɔ"
normalized = normalize_saar(text)
```

## Caractères Problématiques et Substitutions

| Problème | Mauvais | Correct | Note |
|----------|---------|---------|------|
| Schwa mal encodé | `e` simple | `ə` (U+0259) | Très courant |
| O ouvert manquant | `o` normal | `ɔ` (U+0254) | Phonème distinct |
| Implosive perdue | `d` normal | `ɗ` (U+0257) | Phonème distinctif |
| Macron manquant | `a` | `ā` (a + U+0304) | Important pour tons |

## Vérification de l'Encodage

```python
import re

def check_saar_chars(text):
    """Vérifie que le texte contient des caractères Saar valides."""
    saar_chars = r'[ɓɗəɔɛḭḛṵā̰áàâéèêíìîóòôúùû]'
    return bool(re.search(saar_chars, text))

def get_char_list(text):
    """Liste tous les caractères spéciaux du texte."""
    special = r'[^\w\s\.\,\:\;\!\?\-]'
    return set(re.findall(special, text))
```

## Ressources

- **Unicode IPA Extensions**: U+0250–U+02AF
- **Combining Diacritical Marks**: U+0300–U+036F
- **Standard** : ISO 639-3 code `sar` pour Saar/Sara

## Notes pour le ML

1. **Tokenization** : Attention aux caractères diacritiques (ne pas les séparer)
2. **Word Embeddings** : Considérer les diacritiques comme modifiant le phonème
3. **Normalisation** : Toujours appliquer NFC avant traitement
4. **Recherche** : Utiliser des patterns regex Unicode-aware
