# Tokenisation du corpus Sar — diagnostic et recommandations

_Analyse : 2026-09-03. Script : `scripts/eval_tokenizers.py`. Rapport chiffré brut : `docs/TOKENIZATION_EVAL.md`._

## TL;DR

- **Aucun tokeniseur pré-entraîné ne gère le Sar sans perte.** Le meilleur (NLLB-200)
  détruit silencieusement **4 caractères** : `ḭ ḛ ṵ` (voyelles nasales i/e/u précomposées)
  et `ȳ` (y ton bas). Résultat : **27 % des phrases Sar contiennent au moins un `<unk>`**
  irréversible (1,8 % des occurrences de mots, 4,5 % des types).
- Le corpus est **cohérent en NFC** (0 ligne modifiée par NFC, 1 seule par NFKC). Le problème
  n'est pas la normalisation mais le **vocabulaire** : NLLB SentencePiece n'a **pas de
  byte-fallback** (0 token `<0x..>`), donc tout caractère absent → `<unk>` définitif.
- **Recommandation : partir de NLLB-200-distilled-600M + étendre le tokeniseur** (ajouter les
  4 caractères manquants, éventuellement quelques centaines de sous-mots Sar), redimensionner
  les embeddings, fine-tuner en LoRA. C'est le meilleur rapport qualité/effort.
- Le Sar (`sar_Latn`) **n'est pas** dans les 202 langues NLLB → il faut ajouter un token de
  langue `sar_Latn` et initialiser son embedding (copie d'une langue proche, ex. `bam_Latn`
  ou `sag_Latn`).

## Résultats (échantillon 12 000 phrases/langue)

| Tokeniseur | Lang | Round-trip exact | Fertilité (tok/mot) | `<unk>`/1k tok | p95 longueur | byte-fallback |
|---|---|---|---|---|---|---|
| **facebook/nllb-200-distilled-600M** | sar | **74,4 %** | 2,43 | 8,3 | 108 | ❌ |
| facebook/nllb-200-distilled-600M | fra | 100,0 % | 1,61 | 0,0 | 60 | |
| google/mt5-base | sar | 93,5 % | 3,06 | 1,4 | 136 | ✅ (256 tok) |
| google/mt5-base | fra | 100,0 % | 1,89 | 0,0 | 71 | |
| google/byt5-small (octets) | sar | **100,0 %** | 6,22 | 0,0 | 280 | n/a |
| google/byt5-small (octets) | fra | 100,0 % | 5,68 | 0,0 | 211 | |
| xlm-roberta-base / mbart-50 / afro-xlmr-base | sar | 54,6 % | 2,85 | 14,2 | 133 | ❌ |

> mBART-50, XLM-R et **afro-xlmr** partagent le même SentencePiece (250k) : identiques, et
> les pires. Ils perdent en plus `ḿ` (m ton haut, très fréquent : 266 pertes/800 phrases),
> `ǹ`, `Ɩ`, `Ɓ`. L'étiquette « africain » d'afro-xlmr ne change **rien** au tokeniseur.

## Détail du diagnostic NLLB

Caractères Sar **bien gérés** (round-trip OK) : `ə ɔ ɛ ɓ ɗ ā ē ī ō ū á é í ó ú à è ì ò ù
ń ḿ ĺ ŕ ý ȳ→non`, et surtout les **marques combinantes sur lettre de base** :
`ə̄` → `▁ə` + `̄`, `ā̰` → `▁ā` + `̰` (2 pièces mais réversible).

Caractères **cassés** (→ `<unk>`, perte totale) :

| Char | Codepoint | Rôle en Sar | Occurrences perdues / 12k phrases |
|---|---|---|---|
| `ḭ` | U+1E2D | i nasal (précomposé) | 2 945 |
| `ȳ` | U+0233 | y ton bas | 1 014 |
| `ḛ` | U+1E1B | e nasal (précomposé) | 618 |
| `Ḭ` | U+1E2C | I nasal majuscule | 227 |
| `ṵ` | U+1E75 | u nasal (précomposé) | 189 |
| `ẃ` `ẁ` | U+1E83/1E81 | w tonal | ~70 |

**Cause racine — asymétrie d'encodage de la nasalité dans le corpus :**

- `a̰ o̰ ə̰` sont encodés **base + U+0330 combinant** → NLLB : `▁o` + `̰` ✅ réversible
- `ḭ ḛ ṵ` sont encodés en **précomposé NFC** (U+1E2D…) → absent du vocab → `<unk>` ❌

Décomposer (`ḭ` → `i` + U+0330) **ne suffit pas** : le normaliseur interne de NLLB
(nmt_nfkc) **recompose** vers `ḭ` avant lookup. `NFC`, `NFKC`, `NFD` en entrée donnent tous
73,2 % (537/2000 phrases avec `<unk>`) — identique.

## Options

### A. NLLB-200 + tokeniseur étendu ⭐ recommandé
1. `tokenizer.add_tokens(["ḭ","ḛ","ṵ","ȳ","Ḭ","Ḛ","Ṵ","Ȳ","ẃ","ẁ"])` (+ 200–500 sous-mots
   Sar fréquents entraînés par SentencePiece/BPE sur `sar_monolingual.txt` pour faire baisser
   la fertilité de 2,43 → ~1,8).
2. Ajouter le token de langue `sar_Latn`.
3. `model.resize_token_embeddings(len(tokenizer))`, initialiser les nouvelles lignes
   (moyenne des sous-tokens actuels, ou copie d'une langue proche pour `sar_Latn`).
4. Fine-tuning LoRA sur les ~12,7k paires + full-FT des lignes d'embedding neuves.
- **Coût** : faible. **Qualité** : conserve tout le transfert NLLB, corrige la perte.

### B. mT5-base
- Byte-fallback natif → round-trip 93,5 %, `<unk>` rare. Mais : pas un modèle de traduction
  (fine-tuning depuis objectif span-corruption), fertilité plus haute (3,06), séquences +25 %.
- Envisageable si on veut multi-tâches (trad + résumé + POS) sur une seule base.

### C. ByT5-small (octets)
- **Zéro perte, zéro `<unk>`, aucune question de normalisation.** Idéal pour une langue
  tonale à diacritiques empilés.
- Prix : séquences ~4× plus longues (p95 = 280), entraînement/inférence plus lourds,
  contexte effectif réduit. Bon plan B, ou pour un premier prototype « qui marche à coup sûr ».

### D. Tokeniseur maison from scratch (`scripts/tokenize.py`)
- Seulement si entraînement **from scratch** (pas de fine-tuning NLLB). Perd tout le transfert
  cross-lingue — déconseillé vu la taille du corpus (12,7k paires).

## Vérifications à faire avant d'entraîner

1. **Normaliser l'encodage de la nasalité dans le corpus** — choisir UNE convention
   (tout précomposé, ou tout base+U+0330) et l'appliquer partout, y compris à la sortie
   de la plateforme d'annotation DATA4CHAD (clavier SAR).
2. **Round-trip de bout en bout** : `texte → tokeniser → détokeniser → texte'` doit être
   l'identité sur 100 % du corpus après extension du tokeniseur (rejouer
   `scripts/eval_tokenizers.py`).
3. **Cohérence mot ↔ phrase** : vérifier que la tokenisation d'un mot isolé == sa
   tokenisation dans une phrase (important pour l'annotation par mot de DATA4CHAD).
4. **Longueur max** : p95 = 108 tokens Sar sur NLLB → `max_length=128` suffit ;
   prévoir 256 si ByT5.
