# Évaluation des tokeniseurs sur le corpus Sar

_Échantillon : 12000 phrases par langue. Round-trip = decode(encode(x)) == x après NFC._


| Tokeniseur | Lang | Round-trip exact | Round-trip loose | Fertilité (tok/mot) | <unk>/1k | p95 longueur |
|---|---|---|---|---|---|---|
| facebook/nllb-200-distilled-600M | sar | 74.38% | 74.38% | 2.434 | 8.299 | 108 |
| facebook/nllb-200-distilled-600M | fra | 99.97% | 99.97% | 1.608 | 0.009 | 60 |
| google/byt5-small | sar | 100.0% | 100.0% | 6.224 | 0.0 | 280 |
| google/byt5-small | fra | 100.0% | 100.0% | 5.676 | 0.0 | 211 |
| google/mt5-base | sar | 93.53% | 93.53% | 3.059 | 1.398 | 136 |
| google/mt5-base | fra | 100.0% | 100.0% | 1.892 | 0.0 | 71 |

## Détail (codepoints perdus)

### facebook/nllb-200-distilled-600M
- **sar** : {'U+1E2D LATIN SMALL LETTER I WITH TILDE BELOW': 2945, 'U+0233 LATIN SMALL LETTER Y WITH MACRON': 1014, 'U+1E1B LATIN SMALL LETTER E WITH TILDE BELOW': 618, 'U+1E2C LATIN CAPITAL LETTER I WITH TILDE BELOW': 227, 'U+0301 COMBINING ACUTE ACCENT': 193, 'U+1E75 LATIN SMALL LETTER U WITH TILDE BELOW': 189, 'U+0073 LATIN SMALL LETTER S': 129, 'U+0300 COMBINING GRAVE ACCENT': 89, 'U+006E LATIN SMALL LETTER N': 72, 'U+1E83 LATIN SMALL LETTER W WITH ACUTE': 65, 'U+0079 LATIN SMALL LETTER Y': 40, 'U+0304 COMBINING MACRON': 27, 'U+006D LATIN SMALL LETTER M': 22, 'U+0067 LATIN SMALL LETTER G': 13, 'U+006B LATIN SMALL LETTER K': 8}
- **fra** : {'U+2019 RIGHT SINGLE QUOTATION MARK': 1, 'U+0233 LATIN SMALL LETTER Y WITH MACRON': 1, 'U+2013 EN DASH': 1}
### google/byt5-small
- **sar** : aucune perte
- **fra** : aucune perte
### google/mt5-base
- **sar** : {'U+1E1B LATIN SMALL LETTER E WITH TILDE BELOW': 618, 'U+1E2C LATIN CAPITAL LETTER I WITH TILDE BELOW': 227, 'U+0301 COMBINING ACUTE ACCENT': 139, 'U+0073 LATIN SMALL LETTER S': 127, 'U+1E83 LATIN SMALL LETTER W WITH ACUTE': 65, 'U+0079 LATIN SMALL LETTER Y': 24, 'U+0304 COMBINING MACRON': 13, 'U+0300 COMBINING GRAVE ACCENT': 12, 'U+0053 LATIN CAPITAL LETTER S': 6, 'U+1E81 LATIN SMALL LETTER W WITH GRAVE': 4, 'U+0059 LATIN CAPITAL LETTER Y': 3, 'U+0077 LATIN SMALL LETTER W': 1, 'U+006D LATIN SMALL LETTER M': 1, 'U+0067 LATIN SMALL LETTER G': 1, 'U+0050 LATIN CAPITAL LETTER P': 1}
- **fra** : aucune perte

## JSON complet

```json
{
  "facebook/nllb-200-distilled-600M": {
    "vocab_size": 256204,
    "unk_token": "<unk>",
    "sar": {
      "sentences": 12000,
      "roundtrip_exact_%": 74.38,
      "roundtrip_loose_%": 74.38,
      "sent_with_unk_%": 25.625,
      "unk_per_1k_tokens": 8.299,
      "fertility_tok_per_word": 2.434,
      "chars_per_token": 1.865,
      "len_p50": 31,
      "len_p95": 108,
      "len_max": 252,
      "lost_codepoints": {
        "U+1E2D LATIN SMALL LETTER I WITH TILDE BELOW": 2945,
        "U+0233 LATIN SMALL LETTER Y WITH MACRON": 1014,
        "U+1E1B LATIN SMALL LETTER E WITH TILDE BELOW": 618,
        "U+1E2C LATIN CAPITAL LETTER I WITH TILDE BELOW": 227,
        "U+0301 COMBINING ACUTE ACCENT": 193,
        "U+1E75 LATIN SMALL LETTER U WITH TILDE BELOW": 189,
        "U+0073 LATIN SMALL LETTER S": 129,
        "U+0300 COMBINING GRAVE ACCENT": 89,
        "U+006E LATIN SMALL LETTER N": 72,
        "U+1E83 LATIN SMALL LETTER W WITH ACUTE": 65,
        "U+0079 LATIN SMALL LETTER Y": 40,
        "U+0304 COMBINING MACRON": 27,
        "U+006D LATIN SMALL LETTER M": 22,
        "U+0067 LATIN SMALL LETTER G": 13,
        "U+006B LATIN SMALL LETTER K": 8
      }
    },
    "fra": {
      "sentences": 12000,
      "roundtrip_exact_%": 99.97,
      "roundtrip_loose_%": 99.97,
      "sent_with_unk_%": 0.025,
      "unk_per_1k_tokens": 0.009,
      "fertility_tok_per_word": 1.608,
      "chars_per_token": 3.443,
      "len_p50": 26,
      "len_p95": 60,
      "len_max": 116,
      "lost_codepoints": {
        "U+2019 RIGHT SINGLE QUOTATION MARK": 1,
        "U+0233 LATIN SMALL LETTER Y WITH MACRON": 1,
        "U+2013 EN DASH": 1
      }
    }
  },
  "google/byt5-small": {
    "vocab_size": 256,
    "unk_token": "<unk>",
    "sar": {
      "sentences": 12000,
      "roundtrip_exact_%": 100.0,
      "roundtrip_loose_%": 100.0,
      "sent_with_unk_%": 0.0,
      "unk_per_1k_tokens": 0.0,
      "fertility_tok_per_word": 6.224,
      "chars_per_token": 0.729,
      "len_p50": 79,
      "len_p95": 280,
      "len_max": 660,
      "lost_codepoints": {}
    },
    "fra": {
      "sentences": 12000,
      "roundtrip_exact_%": 100.0,
      "roundtrip_loose_%": 100.0,
      "sent_with_unk_%": 0.0,
      "unk_per_1k_tokens": 0.0,
      "fertility_tok_per_word": 5.676,
      "chars_per_token": 0.975,
      "len_p50": 90,
      "len_p95": 211,
      "len_max": 419,
      "lost_codepoints": {}
    }
  },
  "google/mt5-base": {
    "vocab_size": 250100,
    "unk_token": "<unk>",
    "sar": {
      "sentences": 12000,
      "roundtrip_exact_%": 93.53,
      "roundtrip_loose_%": 93.53,
      "sent_with_unk_%": 6.475,
      "unk_per_1k_tokens": 1.398,
      "fertility_tok_per_word": 3.059,
      "chars_per_token": 1.484,
      "len_p50": 39,
      "len_p95": 136,
      "len_max": 319,
      "lost_codepoints": {
        "U+1E1B LATIN SMALL LETTER E WITH TILDE BELOW": 618,
        "U+1E2C LATIN CAPITAL LETTER I WITH TILDE BELOW": 227,
        "U+0301 COMBINING ACUTE ACCENT": 139,
        "U+0073 LATIN SMALL LETTER S": 127,
        "U+1E83 LATIN SMALL LETTER W WITH ACUTE": 65,
        "U+0079 LATIN SMALL LETTER Y": 24,
        "U+0304 COMBINING MACRON": 13,
        "U+0300 COMBINING GRAVE ACCENT": 12,
        "U+0053 LATIN CAPITAL LETTER S": 6,
        "U+1E81 LATIN SMALL LETTER W WITH GRAVE": 4,
        "U+0059 LATIN CAPITAL LETTER Y": 3,
        "U+0077 LATIN SMALL LETTER W": 1,
        "U+006D LATIN SMALL LETTER M": 1,
        "U+0067 LATIN SMALL LETTER G": 1,
        "U+0050 LATIN CAPITAL LETTER P": 1
      }
    },
    "fra": {
      "sentences": 12000,
      "roundtrip_exact_%": 100.0,
      "roundtrip_loose_%": 100.0,
      "sent_with_unk_%": 0.0,
      "unk_per_1k_tokens": 0.0,
      "fertility_tok_per_word": 1.892,
      "chars_per_token": 2.926,
      "len_p50": 30,
      "len_p95": 71,
      "len_max": 134,
      "lost_codepoints": {}
    }
  }
}
```