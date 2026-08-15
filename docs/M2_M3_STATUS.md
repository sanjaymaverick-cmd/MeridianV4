# M2 + M3 Status (15 Aug 2026)

## M2 – Research Baseline  DONE (local → push)
- TBM + uniqueness + purged / CPCV: `src/meta_label/{triple_barrier,purged_cv,uniqueness,m2_research_baseline,predict}.py`
- Artefact: `research/artefacts/meta_label_v4.json`
- Labeled: `data/meta_labels/meridian_v4_meta_labels_tbm.csv`
- Ledger: `research/experiment_ledger.jsonl` (`M2_tbm`)
- Result: y_meta 18.5% (103/557). Purged AUC 0.55 / CPCV 0.58. Synth scaffolding.

## M3 – Decision Engine  SKELETON (next)
- File: `src/decision/engine.py`
- Next: consume artefact `meta_prob`, longer-hold `manage()`, hard gates.

## Blocker
Real clean still ~1 positive. Paper longer-holds required before live promotion.
