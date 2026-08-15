# M4 – OpenAlgo paper path

**Files:** `strategy_v4.py`, `paper_sink.py`, `quotes.py`, `primary.py`, `session.py`

## Run
```
MERIDIAN_MODE=dry python src/openalgo/strategy_v4.py          # demo
MERIDIAN_LOOP=1 MERIDIAN_MAX_TICKS=3 python src/openalgo/strategy_v4.py
MERIDIAN_MODE=paper OPENALGO_API_KEY=... OPENALGO_HOST=http://127.0.0.1:5000 \
  MERIDIAN_LOOP=1 python src/openalgo/strategy_v4.py
```
Paper Analyzer: `client.analyzertoggle(mode=True)` on the OpenAlgo box first.

## Loop
`quotes/multiquotes` → causal primary (`signal_from_quote`) → `decide`/`manage` → `placeorder` or `strategyorder` → SELL appends `is_synthetic=0`.

NSE session 09:15–15:30 IST, flatten 15:15. `BNBUSDT` on DELTA, no cash EOD.

## Env
`MERIDIAN_ROOT`, `MERIDIAN_MODE=dry|paper`, `MERIDIAN_SYMBOLS`, `MERIDIAN_POLL_SEC`, `OPENALGO_API_KEY`, `OPENALGO_HOST`, `OPENALGO_WEBHOOK_ID`.

No secrets in repo. Quote poll requires API key (webhook cannot quote).
