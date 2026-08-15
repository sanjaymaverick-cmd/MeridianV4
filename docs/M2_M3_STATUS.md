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

## M4 – OpenAlgo wrapper  DONE
- Quote poll (`quotes.py`) + IST session + causal primary
- `poll_once` / `run` in `strategy_v4.py`
- paper_sink on SELL (`is_synthetic=0`)

## M5 – Automation  DONE (promotion blocked)
- `src/automation/retrain.py` writes candidates only
- Gates fail on current real: quality 16/25, y_meta+ 2/15, no real purged AUC
- Registry: `research/registry/index.jsonl`

## M6 – Live  GATED
- Kill / daily loss / live 10% cap / max 2 names / ₹25k
- State persist + cooldown + Analyzer preflight
- Checklist: `docs/M6_PRELIVE.md`

## Ship-ready (15 Aug 2026, later same day)
- Project package: `pyproject.toml`, `.env.example`, `src/{settings,paths,logutil}.py`
- Model interface: `src/meta_label/model.py` (`load_model`)
- Engine hardened (NaN, missing artefact, daily roll)
- OpenAlgo host entry: `src/openalgo/host.py`
- Training deferred: `docs/TRAINING_TODO.md`

## Blocker (human — not a code blocker)
Real clean still ~2 TBM+ / 16 quality holds. Run paper when markets open, then `--promote`. Do not live.
