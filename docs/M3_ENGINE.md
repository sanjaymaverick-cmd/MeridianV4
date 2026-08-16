# M3 – Decision Engine

**File:** `src/decision/engine.py`  
**Artefact:** `research/artefacts/meta_label_v4.json`

## Entry (`decide`)
1. EOD gate (`minutes_to_eod < 30` → FLAT)
2. Heat gate (`portfolio_heat ≥ 0.35` → FLAT)
3. `meta_prob` = explicit → artefact logistic → `p_success`
4. Threshold 0.55 (artefact)
5. Size = clip((p−0.5)×1.5×(1−heat), 0, 0.25)
6. Stop = clip(1.5×ATR%, 0.8%, 4%)

## Exit (`manage`) — longer-hold
| Condition | Action |
|-----------|--------|
| R ≤ −1 | SELL hard_stop (even < min hold) |
| minutes_to_eod ≤ 0 (15:15 IST) | SELL eod_flatten |
| held < 300s | HOLD (no scratch) |
| R ≥ 1.5 | SELL take_profit |
| high_R ≥ 1.0 and R ≤ 0.4 | SELL trail |
| else | HOLD |

Live path: no sklearn. JSON sigmoid only.

## Production guards
- NaN / inf features → finite defaults. Never crash the host.
- Missing or corrupt artefact → `p_success` fallback (`UntrainedModel`).
- `Engine` wraps `decide`/`manage` + optional `load_model()`.
- Daily PnL rolls on IST date change (`RiskState.roll_day`).
- `manage` on `last_price <= 0` → HOLD `bad_price`.

Load: `from model import load_model`.
