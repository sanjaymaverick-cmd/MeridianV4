# M2 – Research Baseline (TBM + purged CV)

**Date:** 2026-08-15  
**Artefact:** `research/artefacts/meta_label_v4.json`  
**Labeled set:** `data/meta_labels/meridian_v4_meta_labels_tbm.csv`

## Method
- Triple-barrier in **R-space** (AFML ch.3): PT +1R, SL −1R, vertical 1800s.
- Path = Brownian bridge 0 → realized `y_R` (honest endpoint; first-touch can still assign SL).
- Sample weights = average uniqueness (AFML ch.4).
- Validation = PurgedKFold(4) + CombinatorialPurgedKFold(6 groups / 2 test) + 5min embargo.
- Model = balanced LogisticRegression. Live scorer is JSON (no sklearn).

## Combined set (557 = 157 real + 400 synth)
| TBM | n |
|-----|--:|
| +1 PT | 103 |
| −1 SL | 145 |
| 0 vertical | 309 |
| y_meta wr | 18.5% |

| Split | mean AUC |
|-------|----------|
| Purged K-fold | 0.546 |
| CPCV | 0.584 |
| In-sample | 0.738 |

## Rules
- `is_synthetic=1` is scaffolding. **Do not promote on these metrics.**
- Real clean still has ~1 win — need paper longer-holds before M5/M6.
- Engine threshold = 0.55 (`artefact.threshold`).
