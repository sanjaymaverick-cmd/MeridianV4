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
├── docs/
│   ├── BUILD_PLAN.md              # Master build plan & decisions
│   └── M1_validation_report.md    # Data pipeline validation
├── data/
│   └── meta_labels/               # Cleaned V4 training sets
├── src/
│   └── meta_label/                # Meta-label builders & pipelines
├── research/                      # Notebooks & experiments (M2+)
└── scripts/                       # Utility scripts
```

---

## Current Status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 – Master Spec | Done | This repo + BUILD_PLAN.md |
| M1 – Data Pipeline | Done | Clean 157-row set, longer-hold flags, contamination handling |
| M2 – Research Baseline | Next | mlfinlab triple-barrier + purged CV |
| M3 – Decision Engine | Pending | Pure Python engine |
| M4 – OpenAlgo Paper | Pending | Hosted strategy + closed-loop learning |
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
```

**Important:** Always filter with `is_clean == 1` before any model training.  
Futures contamination is fully flagged and excluded from the clean set.

---

## Principles

1. **Honest accounting** – post-fee, causal features only.
2. **V3 isolation** – V3 files are never modified.
3. **Thin live path** – heavy research stays offline; only the decision engine runs in OpenAlgo.
4. **Reproducibility** – feature hashes + experiment ledger from day one.

---

## Next

Proceed to **M2 – Research Baseline** (mlfinlab-style meta-label pipeline on the clean 157 rows).

---

*Built for systematic edge. No look-ahead. No fantasy fills.*
