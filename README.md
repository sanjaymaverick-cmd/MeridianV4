# Meridian V4

**Production-grade automated quant trading system**  
India equities/F&O + Delta crypto · OpenAlgo execution · mlfinlab-style meta-labeling

---

## Overview

Meridian V4 is the next generation of the Meridian trading system.

- **OpenAlgo** → Trading operating system (multi-broker, Python strategy host, sandbox, monitoring)
- **Focused quant stack** → Research, meta-labeling, risk & portfolio (selected tools from awesome-quant)
- **Meridian Decision Engine** → Thin, deterministic pure-Python layer that sits between research and live execution

### Locked Decisions
| Area | Choice |
|------|--------|
| Markets | India equities/F&O + Delta crypto |
| Meta-label style | Full mlfinlab-style (triple-barrier, sequential bootstrap, purged CV) |
| Holding behaviour | Redesign for longer, higher-quality holds |
| Risk / promotion | Aggressive (once gates are cleared) |
| Strategy style | Pure Python strategy hosted inside OpenAlgo |

---

## Repository Structure

```
MeridianV4/
├── README.md
├── docs/                          # BUILD_PLAN + milestone reports
├── data/meta_labels/              # Clean + synth + TBM-labeled sets
├── src/meta_label/                # TBM, purged CV, builders
├── src/decision/                  # Thin pure-Python engine (M3)
├── src/openalgo/                  # Hosted strategy + quote loop (M4)
├── src/automation/                # Retrain, gates, registry (M5)
├── research/                      # Ledger + artefact + registry
└── tests/
```

---

## Current Status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 – Master Spec | Done | This repo + BUILD_PLAN.md |
| M1 – Data Pipeline | Done | Clean 157-row set, longer-hold flags, contamination handling |
| M2 – Research Baseline | Done | TBM +1R/−1R, uniqueness, purged/CPCV. Artefact JSON. Synth only. |
| M3 – Decision Engine | Done | meta_prob from JSON; longer-hold manage(); hard gates |
| M4 – OpenAlgo Paper | Done | Quote poll + causal primary + paper/dry loop. Analyzer-ready. |
| M5 – Automation Gates | Done | Retrain + real-only gates + registry. Current real fails (expected). |
| M6 – Live | Gated | Code ready. Blocked until M5 gates pass. See `docs/M6_PRELIVE.md`. |

---

## Quick Start (Data)

```bash
# Clean meta-label set (primary training data)
data/meta_labels/meridian_v4_meta_labels.csv
data/meta_labels/meridian_v4_meta_labels.db

# Rebuild / refresh
python src/meta_label/build_meta_labels_v4.py

# M2: TBM labels + purged CV + artefact
python src/meta_label/m2_research_baseline.py

# M4 dry
python src/openalgo/strategy_v4.py

# M5 retrain (candidate only; will not promote on current real)
python src/automation/retrain.py
```

**Important:** Always filter with `is_clean == 1` before any model training.  
Futures contamination is fully flagged and excluded from the clean set.  
`is_synthetic == 1` is scaffolding — not promotion-eligible.

---

## Principles

1. **Honest accounting** – post-fee, causal features only.
2. **V3 isolation** – V3 files are never modified.
3. **Thin live path** – heavy research stays offline; only the decision engine runs in OpenAlgo.
4. **Reproducibility** – feature hashes + experiment ledger from day one.

---

## Next

**You do next:** run paper (`scripts/paper_loop.ps1`) until gates pass, then `docs/M6_PRELIVE.md`. Software stack M0–M6 is in-repo.

---

*Built for systematic edge. No look-ahead. No fantasy fills.*
