# Meridian V4

**Production-grade automated quant trading system**  
India equities/F&O + Delta crypto · OpenAlgo execution · mlfinlab-style meta-labeling

Training is **later**. The application is ship-ready without live fills.

---

## Locked Decisions

| Area | Choice |
|------|--------|
| Markets | India equities/F&O + Delta crypto |
| Meta-label style | Full mlfinlab-style (TBM, uniqueness, purged CV) |
| Holding | Longer, higher-quality holds (min 300s) |
| Risk / promotion | Aggressive once gates clear |
| Strategy | Pure Python hosted inside OpenAlgo |
| V3 | Never touch V3 files |

---

## Layout

```
MeridianV4/
├── src/settings.py paths.py logutil.py
├── src/decision/engine.py          # live path (no sklearn)
├── src/meta_label/
│   ├── model.py                    # load_model() interface
│   ├── predict.py                  # JSON logistic scorer
│   ├── train.py                    # TODO(training) LightGBM stub
│   ├── triple_barrier.py purged_cv.py uniqueness.py
│   └── m2_research_baseline.py     # current trainer (logistic JSON)
├── src/openalgo/
│   ├── host.py                     # OpenAlgo /python upload entry
│   ├── strategy_v4.py              # hosted loop
│   ├── quotes.py primary.py session.py broker.py paper_sink.py state.py
├── src/automation/                 # retrain + real-only gates + registry
├── data/meta_labels/               # clean + synth + TBM
├── research/artefacts/meta_label_v4.json
├── docs/                           # BUILD_PLAN + milestone notes
└── tests/
```

---

## Status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 Master Spec | Done | `docs/BUILD_PLAN.md` |
| M1 Data Pipeline | Done | 157 clean real rows |
| M2 Research Baseline | Done | TBM + purged/CPCV. Synth scaffolding (557). |
| M3 Decision Engine | Done | Production guards. JSON `meta_prob`. |
| M4 OpenAlgo wrapper | Done | Hostable. Paper/dry. SIGTERM. |
| M5 Automation / gates | Done | Real-only promotion. Current real **fails** (expected). |
| M6 Live | Gated | See `docs/M6_PRELIVE.md`. |
| Training | **Later** | `docs/TRAINING_TODO.md` |

Synth (`is_synthetic=1`) may scaffold models. It **cannot** promote.

---

## Install

```powershell
cd "D:\work Dir\MeridianV4"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# optional: pip install openalgo yfinance
copy .env.example .env   # then edit; never commit
```

---

## Run

### Offline (no market, no broker)

```powershell
# tests
python -m pytest tests
# or: .\scripts\run_tests.ps1

# dry demo
$env:MERIDIAN_MODE = "dry"
python src/openalgo/strategy_v4.py
# or: .\scripts\run_dry.ps1

# dry poll loop (synthetic book empty unless you push ticks)
$env:MERIDIAN_LOOP = "1"
$env:MERIDIAN_MAX_TICKS = "3"
python src/openalgo/strategy_v4.py
```

### OpenAlgo paper (Analyzer ON — when markets are open)

```powershell
.\scripts\start_openalgo.ps1          # separate box / checkout
$env:OPENALGO_API_KEY = "<from OpenAlgo UI>"
.\scripts\paper_loop.ps1
```

Or upload `src/openalgo/host.py` to OpenAlgo → Python Strategies.  
Set `MERIDIAN_ROOT` in OpenAlgo `.env` to this repo (absolute path).  
Do **not** set `MERIDIAN_LIVE_OK`. Analyzer **ON**.

### Retrain / gates (will not promote on current real)

```powershell
python src/automation/retrain.py              # candidate only
python src/automation/retrain.py --promote    # promote iff gates pass
python src/automation/gates.py                # exit 0 only if last eval passed
```

### Kill / rollback

- Stop entries: create `research/runtime/KILL`
- Rollback live artefact: `python -c "import sys; sys.path.insert(0,'src/automation'); from registry import rollback; rollback()"`

---

## Model interface

```python
from model import load_model
m = load_model()            # JsonLogisticModel or UntrainedModel
p = m.predict(features)     # [0, 1]
```

Live path: JSON artefact, no sklearn.  
Missing/corrupt artefact → `UntrainedModel` (primary `p_success`).  
`LightGBMModel` is a `TODO(training)` stub.

Always filter training rows with `is_clean == 1`.  
`is_synthetic == 1` is not promotion-eligible.

---

## Env

See `.env.example`. Hosted scripts also receive `OPENALGO_API_KEY`, `OPENALGO_HOST`, `STRATEGY_NAME`, `STRATEGY_ID`, `OPENALGO_STRATEGY_EXCHANGE`.

No secrets in git.

---

## Next

Paper fills when NSE is open → `docs/TRAINING_TODO.md`. Then `--promote`. Then `docs/M6_PRELIVE.md`.
