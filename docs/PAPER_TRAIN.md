# Paper-only training (current mission)

**No live. No Auto. Analyzer ON.** Goal: honest longer-hold fills → `meridian_v4_paper_fills.csv` → `retrain.py`.

## Why
Real clean set: 157 rows, 16 quality holds, ~2 TBM+. Gates fail. Synth cannot promote.

## Loop
1. OpenAlgo up, Analyzer **ON**, logged into broker (Zerodha for NSE).
2. Kite **Personal** has no LTP → Meridian falls back to Yahoo for quotes, still **orders Analyzer**.
3. Session hours (Mon–Fri 09:15–15:15 IST): MIS MARKET.
4. After hours / weekend: CNC LIMIT (sandbox record only — prefer weekday for quality holds).
5. Closes append `is_synthetic=0` to `data/meta_labels/meridian_v4_paper_fills.csv`.
6. When paper quality holds ≥ 25 and TBM+ ≥ 15: `python src/automation/retrain.py --no-synth --promote`.

```
$env:OPENALGO_API_KEY = "<OpenAlgo UI key>"
$env:MERIDIAN_MODE = "paper"
$env:MERIDIAN_LOOP = "1"
$env:MERIDIAN_POLL_SEC = "30"
Set-Location "D:\work Dir\MeridianV4"
python src/openalgo/strategy_v4.py
```

Do **not** set `MERIDIAN_LIVE_OK`. Do **not** turn Analyzer off.

Delta crypto = later paper slice (separate Delta login). Not this week’s blocker.
