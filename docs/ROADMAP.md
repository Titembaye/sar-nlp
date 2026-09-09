# Feuille de route — Valorisation du Sar par le NLP

_Version 1 — 2026-09-03. Document vivant : mettre à jour les cases à cocher et les chiffres à chaque jalon._

## 1. Vision

Construire progressivement un écosystème d'outils NLP pour le **sar** (langue sara, Tchad,
ISO 639-3 `sar`), en partant des données déjà collectées et en montant par paliers :
socle de données propre → tokenisation → traduction → boucle d'agrandissement du corpus →
modèle de langue → outils linguistiques et parole.

**Principe directeur : le goulot n'est pas le modèle, c'est le corpus.** 12,7 k paires =
très basses ressources. Chaque phase doit soit augmenter la quantité/qualité/diversité des
données, soit rendre la suivante possible. On ne saute pas d'étape.

## 2. État actuel (2026-09-03)

| Ressource | Volume | Note |
|---|---|---|
| Paires Sar↔Fr | **12 717** | 8 726 Bible · 3 193 dictionnaire · 798 lexique Sara |
| — dont doublons exacts | 104 | à dédupliquer |
| — dont entrées 1-2 mots | 812 | lexique, pas des phrases |
| Phrases Sar distinctes | ~12 452 | |
| Monolingue Sar | 26 389 lignes / ~342 k mots | |
| Vocabulaire Sar | ~11 400 formes | 739 hapax ; top-2000 couvre 93 % |
| Français monolingue (Tatoeba) | 100 000 phrases | pour back-translation |
| DATA4CHAD (annotation) | 147 935 items chargés | plateforme opérationnelle |

**Biais principal : ~80 % du bilingue est de registre biblique.** Priorité transversale =
diversifier les domaines.

## 3. Contraintes

- **Compute : Colab / Kaggle gratuit uniquement.** GPU T4/P100, sessions 9–12 h,
  interruptions. → LoRA sur `NLLB-200-distilled-600M` (4-bit), pas de pré-entraînement
  from scratch. Tout entraînement doit être **checkpointé et reprenable** (sauvegarde vers
  Drive ou HF Hub à chaque N steps).
- **Équipe : 1 dev + annotateurs sur DATA4CHAD.** → les guides d'annotation, les conventions
  écrites et le contrôle qualité inter-annotateur sont des livrables de première classe,
  pas des à-côtés.
- **Licences.** Bible SARDC : non publiable sans accord Alliance Biblique du Tchad.
  Dictionnaire / cosmogonie : accord des ayants droit requis. **Seuls les modèles entraînés
  et les données 100 % originales (annotation DATA4CHAD) sont publiables librement.**

## 4. Phases

Chaque phase liste : objectif · tâches · livrables · **critères de sortie** (mesurables).
On ne passe à la phase suivante que si les critères de sortie sont verts.

---

### Phase 0 — Socle de données ⏳ EN COURS

**Objectif :** un corpus canonique unique, normalisé, versionné, avec des splits gelés.

**Tâches**
- [ ] `scripts/build_canonical.py` : fusionne toutes les sources en `data/canonical/corpus.jsonl`
      avec schéma `{id, sar, fr, source, domain, licence, split}`.
- [ ] Déduplication : 104 doublons exacts + arbitrage des 213 Sar à Fr multiples.
- [ ] **Décision normalisation Unicode** (bloquante — voir `docs/TOKENIZATION.md`) :
      figer NFC + UNE convention pour la nasalité (tout précomposé, ou tout base + U+0330).
      `scripts/normalize.py` idempotent (`normalize(normalize(x)) == normalize(x)`).
- [ ] Appliquer `normalize.py` : au corpus, au clavier SAR de DATA4CHAD (khalima-frontend),
      au pipeline d'import ETL. Une seule fonction, importée partout.
- [ ] Splits `train` / `dev` / `test` **sans fuite** : dédup inter-splits sur le Sar ET sur
      le Fr, test set stratifié par domaine, **gelé** (hash commité, jamais régénéré).
- [ ] `docs/DATASHEET.md` : provenance, volumes, licences, biais connus, prétraitements.
- [ ] Statut licences écrit noir sur blanc (qui contacter, quoi est publiable).

**Livrables :** `data/canonical/corpus.jsonl`, `scripts/normalize.py`, `scripts/build_canonical.py`,
splits gelés, `docs/DATASHEET.md`.

**Critères de sortie**
- Round-trip `texte → normalize → dénormalise` = identité sur 100 % du corpus.
- 0 doublon exact, 0 fuite train/test (vérifié par script).
- Test set gelé et documenté (taille cible : ~1 000 paires, ≥3 domaines).
- Toute nouvelle donnée entrant par DATA4CHAD ressort déjà normalisée.

---

### Phase 1 — Tokenisation

**Objectif :** un tokeniseur qui n'efface aucune information sar, gelé en v1.

**Tâches**
- [ ] `scripts/build_tokenizer.py` : partir de `facebook/nllb-200-distilled-600M`,
      `add_tokens` des caractères cassés (`ḭ ḛ ṵ ȳ` + majuscules + `ẃ ẁ`), ajouter le
      token de langue `sar_Latn`.
- [ ] Entraîner ~300–500 sous-mots sar (SentencePiece/BPE sur le monolingue) et les ajouter,
      pour faire tomber la fertilité de 2,43 vers ~1,8 tok/mot.
- [ ] Script d'init des embeddings des nouveaux tokens (moyenne des sous-tokens ;
      `sar_Latn` ← copie d'une langue proche, ex. `bam_Latn` ou `sag_Latn`).
- [ ] Rejouer `scripts/eval_tokenizers.py` sur le tokeniseur étendu.

**Livrables :** `models/tokenizer_sar_v1/`, section « v1 » ajoutée à `docs/TOKENIZATION.md`.

**Critères de sortie**
- Round-trip exact = **100 %** sur tout le corpus sar (0 `<unk>`).
- Fertilité sar ≤ 2,0 tok/mot.
- Tokenisation d'un mot isolé == sa tokenisation dans une phrase (test sur 500 mots).
- Tokeniseur taggé (`v1`) et figé ; toute évolution future = `v2`, jamais d'écrasement.

---

### Phase 2 — Baseline de traduction

**Objectif :** un premier modèle Sar↔Fr honnête, mesuré, publié.

**Tâches**
- [ ] Notebook Colab/Kaggle : NLLB-distilled-600M 4-bit + LoRA, `max_length=128`,
      batch effectif via accumulation, checkpoint → HF Hub toutes les N steps, reprise auto.
- [ ] Entraîner les deux directions (un seul modèle multi-directions).
- [ ] `scripts/evaluate.py` : chrF++ et BLEU (sacrebleu) sur le test gelé, par domaine.
      COMET si le temps GPU le permet.
- [ ] Baselines de référence : (a) lookup dictionnaire mot-à-mot, (b) NLLB zero-shot via
      une langue proche. Le modèle doit battre les deux.
- [ ] **Éval humaine** : 100 phrases test notées par un locuteur natif (adéquation +
      fluidité, échelle 1–5). Grille dans `docs/EVAL_HUMAINE.md`.
- [ ] Publier `saar-nllb-v0.1` sur HF Hub + carte de modèle (données, métriques, limites,
      biais biblique explicite).

**Livrables :** modèle v0.1 sur HF, `scripts/evaluate.py`, `docs/RESULTS.md`, grille d'éval humaine.

**Critères de sortie**
- chrF++ sar→fr et fr→sar reportés par domaine sur le test gelé.
- Modèle > les deux baselines triviales sur chrF++.
- Éval humaine : adéquation moyenne ≥ 3/5 sur au moins un domaine.
- Carte de modèle publiée, résultats reproductibles depuis le notebook commité.

---

### Phase 3 — Boucle d'agrandissement du corpus 🎯 phase-clé

**Objectif :** passer de 12 k à 30 k puis 50 k paires humaines, en diversifiant les domaines.

**Tâches**
- [ ] Endpoint `/api/translate/` dans khalima-backend servant le modèle v0.1 (HF Inference
      ou modèle chargé sur Render — attention RAM free tier ; sinon HF Inference API).
- [ ] DATA4CHAD : mode « suggestion machine → correction humaine » dans le flux d'annotation.
- [ ] **Active learning** : prioriser dans la file les phrases où le modèle est le moins sûr
      (faible proba, désaccord back-translation) et celles contenant des nasales/tons rares.
- [ ] **Guide d'annotation** `docs/GUIDE_ANNOTATION.md` : orthographe, nasalité, tons,
      segmentation des mots, variantes dialectales, quoi faire des cas douteux.
- [ ] **Contrôle qualité** : double annotation sur 5–10 % des items, mesure d'accord
      inter-annotateur (chrF entre annotateurs + taux d'accord exact), rôle « relecteur »
      dans DATA4CHAD.
- [ ] **Back-translation** : traduire Tatoeba-fr (100 k) → sar synthétique par lots sur
      plusieurs sessions ; marquer `source=backtranslation` ; ré-entraîner v0.2 en mélangeant
      (ratio synthétique/humain à calibrer, typiquement 1:1 à 3:1).
- [ ] Collecte ciblée de sources nouvelles hors registre biblique (radio, presse locale,
      santé, agriculture, contes) — avec autorisations.

**Livrables :** endpoint traduction, guide d'annotation, rapport IAA, modèle v0.2,
corpus élargi versionné (`corpus.jsonl` v2).

**Critères de sortie**
- ≥ 30 000 paires humaines validées, dont ≥ 30 % hors registre biblique.
- Accord inter-annotateur documenté (cible : accord exact ≥ 0,6 ou chrF inter-annot ≥ 60).
- v0.2 > v0.1 sur le test gelé (gain chrF++ mesuré).
- Guide d'annotation suivi par tous les annotateurs (relu, versionné).

---

### Phase 4 — Modèle de langue sar monolingue

**Objectif :** une base réutilisable pour les tâches linguistiques (pas de la traduction).

**Tâches**
- [ ] Rassembler tout le monolingue sar disponible (corpus actuel + apports Phase 3 +
      côté sar des nouvelles paires).
- [ ] *Continued pretraining* léger (MLM) d'un encodeur existant (`Davlan/afro-xlmr-base`
      ou `xlm-roberta-base`) sur le monolingue sar — faisable en LoRA/adapter sur free tier.
      Pas de modèle from scratch (corpus trop petit, compute insuffisant).
- [ ] Publier `saar-encoder-v0.1` sur HF Hub.

**Livrables :** encodeur sar adapté, carte de modèle.

**Critères de sortie**
- Perplexité / pseudo-perplexité MLM en baisse nette vs modèle de base sur un dev sar.
- Le modèle sert au moins une tâche aval en Phase 5 (détection de langue ou POS).

---

### Phase 5 — Outils linguistiques et parole

**Objectif :** transformer les modèles en outils utiles aux locuteurs et chercheurs.

**Pistes** (à prioriser selon les besoins réels — ne pas tout faire) :
- [ ] Détecteur de langue sar (utile pour filtrer/collecter du web).
- [ ] Correcteur orthographique / normaliseur (nasalité, tons) — fort impact vu
      l'hétérogénéité d'écriture.
- [ ] POS tagging + petit treebank (annotation DATA4CHAD, guidelines UD).
- [ ] Analyseur morphologique (langue agglutinante) — segmentation morphèmes.
- [ ] Dictionnaire numérique enrichi : lemmatisation, définitions, exemples liés au corpus.
- [ ] **ASR / TTS** : activer l'annotation audio de DATA4CHAD (modèle `AudioDataset`,
      stockage Supabase/S3, enregistreur frontend), viser un premier corpus parole aligné,
      fine-tune Whisper (ASR) et un TTS léger.
- [ ] API publique + démo web.

**Critères de sortie :** au moins 2 outils publiés et documentés, utilisés en dehors du projet.

---

## 5. Ordre et jalons

```
Phase 0 ──▶ Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5
(données)   (tokens)    (v0.1)      (corpus×3)   (encodeur)  (outils)
                                    ▲     │
                                    └─────┘  boucle : v0.2, v0.3…
```

- **Jalon A** : Phase 0 + 1 finies → socle gelé, prêt pour l'entraînement.
- **Jalon B** : modèle v0.1 publié + mesuré → preuve que la chaîne fonctionne.
- **Jalon C** : 30 k paires + v0.2 → la boucle d'agrandissement tourne.
- **Jalon D** : 50 k paires + encodeur sar → base pour les outils.

Phases 0→2 sont séquentielles. À partir de la Phase 3, la boucle
(annotation → ré-entraînement → meilleure suggestion → annotation) tourne en continu et les
Phases 4–5 se greffent dessus.

## 6. Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Incohérence d'écriture du sar (tons/nasales) | corrompt tout l'entraînement | Phase 0 normalisation stricte, appliquée à la source |
| Corpus reste trop biblique | modèle inutilisable en langue courante | Phase 3 : quota domaines, collecte ciblée |
| Peu d'annotateurs / lassitude | boucle Phase 3 s'essouffle | suggestions machine (moins d'effort), objectifs courts, feedback visible |
| Compute free insuffisant | entraînements qui n'aboutissent pas | 4-bit + LoRA + checkpoint reprenable dès le départ |
| Licences bloquantes pour publier | pas de diffusion possible | ne publier que modèles + données originales ; négocier les accords en parallèle |
| Fuite train/test | métriques faussées, surprise en prod | test set gelé + script anti-fuite en CI légère |

## 7. Suivi

- Ce fichier = source de vérité de l'avancement (cases à cocher + chiffres à jour).
- Un `data/canonical/corpus.jsonl` versionné (release datée à chaque palier de taille).
- `docs/RESULTS.md` : tableau des versions de modèle et de leurs métriques.
- Chaque modèle publié = une carte de modèle avec données, métriques, limites.
