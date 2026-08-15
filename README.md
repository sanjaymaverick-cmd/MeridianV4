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
├── src/openalgo/                  # Hosted strategy wrapper (M4)
├── research/                      # Ledger + JSON model artefact
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
| M4 – OpenAlgo Paper | Skeleton | `strategy_v4.py` dry/paper + paper_sink. Quote poll TBD. |
| M5 – Automation Gates | Pending | Retrain + promotion rules |
| M6 – Live | Pending | Small capital → production |

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

Proceed to **M4 quote loop** (Historify/OpenAlgo quotes) then **M5 gates**.

---

*Built for systematic edge. No look-ahead. No fantasy fills.*
