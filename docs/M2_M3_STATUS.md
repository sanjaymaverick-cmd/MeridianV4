# M2 + M3 Status (15 Aug 2026)

## M2 – Research Baseline  DONE (local → push)
- TBM + uniqueness + purged / CPCV: `src/meta_label/{triple_barrier,purged_cv,uniqueness,m2_research_baseline,predict}.py`
- Artefact: `research/artefacts/meta_label_v4.json`
- Labeled: `data/meta_labels/meridian_v4_meta_labels_tbm.csv`
- Ledger: `research/experiment_ledger.jsonl` (`M2_tbm`)
- Result: y_meta 18.5% (103/557). Purged AUC 0.55 / CPCV 0.58. Synth scaffolding.

## M3 – Decision Engine  DONE
- File: `src/decision/engine.py` + `docs/M3_ENGINE.md`
- Consumes `meta_label_v4.json` (no sklearn).
- `decide()` + `manage()` (min hold 300s, hard stop, TP 1.5R, trail).
- Tests: `tests/test_m3_engine.py`

## M4 – OpenAlgo wrapper  SKELETON
- `src/openalgo/strategy_v4.py` dry/paper Host
- `src/openalgo/paper_sink.py` appends closes (`is_synthetic=0`)
- Missing: live quote poll / Historify

## Blocker
Real clean still ~1 positive. Paper longer-holds required before live promotion.
