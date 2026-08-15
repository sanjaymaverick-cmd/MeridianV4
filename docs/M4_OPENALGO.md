# M4 – OpenAlgo wrapper (skeleton)

**Files:** `src/openalgo/strategy_v4.py`, `src/openalgo/paper_sink.py`

## Host
1. Set `MERIDIAN_ROOT` to this repo.
2. Upload/run `strategy_v4.py` in OpenAlgo Python Strategy Host.
3. `MERIDIAN_MODE=dry` (default) or `paper`.
4. Paper needs `OPENALGO_HOST` + `OPENALGO_WEBHOOK_ID` (create strategy, platform=Python).

## Loop
`on_signal(Signal, last_price)` → `decide` / `manage` → `strategyorder` → on SELL, `append_close` to `data/meta_labels/meridian_v4_meta_labels.csv` (`is_synthetic=0`).

## Markets
NSE cash (MIS, EOD flatten) + `BNBUSDT` on DELTA. No other venues.

## Not yet
Broker quote poll, Historify bars, Telegram, Analyzer P&L sync. Next: wire quotes + schedule.
