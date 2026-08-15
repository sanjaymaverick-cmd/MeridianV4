# Synthetic Data Note (M2 continuation)

**Generated:** 15 Aug 2026 by Grok

## Why
Real clean set had only 1 win / 157 rows → impossible to train meaningful meta-label model.

## What was generated
- 400 synthetic honest round-trips
- Target longer-hold regime (55% quality holds ≥300s)
- Win rate ~33% on synth (combined 24.1%)
- Features sampled from real clean distributions
- All rows marked `is_synthetic = 1`
- Combined file: `data/meta_labels/meridian_v4_meta_labels_synth.csv` (557 rows)

## Baseline results on combined set
TimeSeriesSplit (4 folds) LogisticRegression:
- Fold 0 AUC 0.71
- Fold 1 AUC 0.59
- Fold 2 AUC 0.55
- Fold 3 AUC 0.54

## Important
This is **scaffolding data** only.  
Real longer-hold paper fills must replace/augment it before any live promotion.  
All synthetic rows are explicitly flagged.
