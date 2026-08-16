# Training phase (do not start until markets are open)

Code is ship-ready. **Do not block the app on this list.**

## Blockers (real data)
- Real clean quality holds ≥ 25 (`hold_sec ≥ 300`)
- Real TBM+ (`y_meta == 1`) ≥ 15
- Paper fills in `data/meta_labels/meridian_v4_paper_fills.csv` with `is_synthetic=0`
- Analyzer ON. No live. No `--force`.

## TODO(training) — still waiting on **real paper fills**
1. Collect paper longer-holds via `scripts/paper_loop.ps1` (weekday NSE session).
2. `python src/automation/retrain.py --no-synth --promote`
3. `python src/automation/gates.py` must exit 0.
4. Only then consider `docs/M6_PRELIVE.md`.

Code now in: LightGBM `fit_lightgbm` + `LightGBMModel`, sequential bootstrap in retrain, JSON logistic still the live fallback. Promote copies `.txt` sidecar if present.

Synth (`is_synthetic=1`, 557-row combined set) is scaffolding. It may train a candidate. It must never pass promotion gates.
