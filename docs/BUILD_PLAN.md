# Meridian V4 – Build Master Spec

**Last updated:** 15 Aug 2026  
**Status:** Active build – M2 complete (synth scaffolding)  
**Location:** `/home/workdir/artifacts` (temporary; V4 will move to separate repo provided by user)

---

## 1. Goal

Production-ready automated quant trading system:

- **OpenAlgo** = Trading OS (execution, multi-broker, Python strategy host, sandbox, monitoring, UI)
- **Focused awesome-quant tools** = Research & intelligence layer
- **Meridian Decision Engine** = Thin, deterministic layer between research and execution

Primary markets (locked): **India equities/F&O + Delta crypto**  
Strategy style (locked): **Pure Python strategy hosted inside OpenAlgo**

---

## 2. Locked Decisions (15 Aug 2026)

| Question | Choice | Implication |
|----------|--------|-------------|
| Market Scope | India + Delta crypto | Use OpenAlgo native plugins. No early global/IBKR complexity. |
| Meta-label style | Full mlfinlab-style | Triple-barrier labels, sequential bootstrap, purged CV from the start. |
| Holding behaviour | Redesign for longer, higher-quality holds | Drop pure scratch/EOD-flatten dominance. New exit logic required. |
| Risk / promotion | Aggressive | Faster promotion once metrics clear gates. Still require documented gates. |
| Strategy style | Pure Python in OpenAlgo | Single decision engine script hosted via OpenAlgo Python Strategy Host. |

---

## 3. Architecture (Final)

```
Research Layer (offline / scheduled)
  ├── Data (OpenAlgo Historify + ccxt + yfinance)
  ├── Features (causal + mlfinlab structures)
  ├── Meta-label model (mlfinlab + LightGBM)
  └── Experiment ledger + model registry
          ↓ artefacts only
Meridian Decision Engine (pure Python)
  ├── Primary signal features
  ├── Meta probability
  ├── Belief / regime
  ├── Position sizing + risk gates
  └── Order intent
          ↓
OpenAlgo (production)
  ├── Python Strategy Host
  ├── Analyzer (paper)
  ├── Live brokers (India + Delta)
  ├── Action Center
  └── Monitoring + Telegram/MCP
```

**Approved library shortlist (do not expand without decision):**
- Meta-label / ML: mlfinlab patterns, LightGBM, sklearn, Optuna
- Backtest: vectorbt + nautilus_trader (or Lean)
- Portfolio / Risk: PyPortfolioOpt, Riskfolio-Lib, empyrical / quantstats
- Indicators: TA-Lib / ta, arch, statsmodels, exchange_calendars
- Data: OpenAlgo Historify, ccxt, yfinance
- Runtime: OpenAlgo only

---

## 4. Build Milestones (Optimized)

**M0 – Master Spec**  
This document.  

**M1 – Data Pipeline**  
Harden meta-label builder. Causal features only. Explicit futures handling. Validation report. Schema ready for continuous append-on-close. New columns for longer-hold regime.  

**M2 – Research Baseline**  
Full mlfinlab-style meta-label pipeline (triple-barrier + purged CV). First tracked model + experiment ledger on clean data.  

**M3 – Decision Engine**  
Standalone pure-Python engine with new longer-hold logic, meta-prob sizing, and hard risk gates. Fully testable offline.  

**M4 – OpenAlgo Paper Path**  
Engine wrapped as OpenAlgo-hosted strategy. Closes automatically enrich training set. Full paper loop in Analyzer.  

**M5 – Automation & Gates**  
Retrain job + aggressive but documented promotion criteria + model registry.  

**M6 – Live + Expansion**  
Small live capital → multi-broker → portfolio heat → monitoring hardening.

---

## 5. Current V3 Baseline & Known Issues

- 199 honest round-trips (single day, 14 Aug 2026)
- Honest win rate: 21.6%
- Heavy short-hold / fee-paying scratches
- Futures mark artefacts (NIFTY.F / INFY.F)
- Fixed belief posterior
- Files: `meridian_v3_meta_labels.csv`, `meridian_v3_with_meta_labels.db`, `build_meta_labels.py`

**Must fix in M1:**  
Futures marks, exit_reason completeness, cooldown, longer-hold redesign foundation.

---

## 6. File Conventions & Isolation Rules

**CRITICAL – V3 Isolation**
- **NEVER edit, overwrite, or modify any V3 files.**
- V3 files (read-only): `build_meta_labels.py`, `meridian_v3_meta_labels.csv`, `meridian_v3_with_meta_labels.db`, `README_MeridianV3_MetaLabels.md`
- If V3 data is needed, always work on a copy.
- All V4 work uses new files only (`*_v4.*`, `Meridian_V4_*`, `M1_*`, etc.).
- User will provide a **separate repository for V4** later. Current artifacts are scaffolding only.

**General**
- Persistent deliverables → `/home/workdir/artifacts`
- Temporary / generation scripts → `/tmp`
- Master docs: `Meridian_V4_*.md`
- Never commit secrets or live API keys.

---

## 7. Current Progress

| Milestone | Status | Key Outputs |
|-----------|--------|-------------|
| M0 Master Spec | Done | `BUILD_PLAN.md`, `README.md` |
| M1 Data Pipeline | Done | `build_meta_labels_v4.py`, `meridian_v4_meta_labels.csv/.db`, `M1_validation_report.md` |
| M2 Research Baseline | Done | TBM + purged/CPCV, `meta_label_v4.json`, `docs/M2_RESEARCH.md` |
| M3 Decision Engine | Next | Harden `src/decision/engine.py` |

**M1 Results (clean subset):** 157 clean rows | 16 quality holds (≥300s) | 173 short holds | Contaminated futures fully flagged and excluded from clean set.

---

## 8. Next Action

Proceed to **M3 – Decision Engine** (meta_prob from artefact, longer-hold manage, hard gates).

---

*This document is the single source of truth for Meridian V4 build decisions.*
