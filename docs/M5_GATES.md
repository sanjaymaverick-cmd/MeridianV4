# M5 – Retrain, registry, promotion

**Files:** `src/automation/{retrain,gates,registry}.py`  
**Live artefact:** `research/artefacts/meta_label_v4.json`  
**Candidates:** `research/artefacts/candidates/`  
**Registry:** `research/registry/index.jsonl`

## Run
```
python src/automation/retrain.py              # candidate only
python src/automation/retrain.py --promote    # promote iff gates pass
python src/automation/retrain.py --no-synth --promote
# --force logs FORCE and overwrites live — ops only
```

## Gates (real rows only — `is_synthetic` never counts)

| Check | Floor (aggressive) |
|-------|-------------------|
| n_real_clean | ≥ 80 |
| n_real_quality (≥300s) | ≥ 25 |
| n_real y_meta +1 | ≥ 15 |
| purged / CPCV AUC | ≥ 0.55 |
| in-sample − purged | ≤ 0.18 |
| quality hold frac | ≥ 0.25 |
| n_synth_in_eval | 0 |

**Current real set fails** (16 quality, ~1 TBM+). Expected. Do not `--force` for live.

Train may use synth; **promotion metrics cannot**.

```
python src/automation/gates.py          # exit 0 only if last registry eval passed
python -c "import sys; sys.path.insert(0,'src/automation'); from registry import rollback; rollback()"
```

Task Scheduler: `scripts/retrain_daily.ps1` after close. Paper: `scripts/paper_loop.ps1`.

LightGBM trainer is a stub (`src/meta_label/train.py`). Current `retrain.py` writes logistic JSON candidates. See `docs/TRAINING_TODO.md`.
