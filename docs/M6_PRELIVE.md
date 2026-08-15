# M6 – Pre-live checklist

**Do not go live until every box is true.** `--force` is not a substitute.

## Gates (M5)
- [ ] `python src/automation/gates.py` exits 0
- [ ] Registry has a `promoted` row (not `force`)
- [ ] Eval used `is_synthetic=0` only
- [ ] Real quality holds ≥ 25 and TBM+ ≥ 15

## OpenAlgo
- [ ] Analyzer **OFF** for live (`refuse_live_if_analyzer`)
- [ ] Analyzer **ON** for paper
- [ ] India broker + Delta plugin only
- [ ] `OPENALGO_API_KEY` in env, never committed
- [ ] `MERIDIAN_LIVE_OK=1` set only after gates pass

## Risk
- [ ] Live budget ₹25k (`LIVE_BUDGET`)
- [ ] Live size cap 10%, max 2 names
- [ ] Daily loss −₹5k flatten
- [ ] Kill file `research/runtime/KILL` stops entries
- [ ] 10 min cooldown after hard_stop/trail
- [ ] Telegram username set if you want alerts

## Run
```
# paper first (days, not hours)
MERIDIAN_MODE=paper OPENALGO_API_KEY=... MERIDIAN_LOOP=1 python src/openalgo/strategy_v4.py

# live (after checklist)
MERIDIAN_MODE=live MERIDIAN_LIVE_OK=1 OPENALGO_API_KEY=... MERIDIAN_LOOP=1 python src/openalgo/strategy_v4.py
```

Stop live: create `research/runtime/KILL` or unset `MERIDIAN_LIVE_OK`.
Rollback model: `python -c "from registry import rollback; rollback()"` from `src/automation`.
