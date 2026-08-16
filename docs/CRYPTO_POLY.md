# Crypto + Polymarket

## Crypto (Delta / 24h)

OpenAlgo **DELTA** USDT perps. No cash EOD. Default watch now includes `BTCUSDT,ETHUSDT,BNBUSDT`.

| Meridian | Yahoo (backfill) |
|----------|------------------|
| BTCUSDT … UNIUSDT | BTC-USD … UNI-USD |

```
MERIDIAN_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT MERIDIAN_MODE=paper python src/openalgo/strategy_v4.py
python src/data/backfill_5y.py --markets crypto
```

Qty is fractional (`0.001` min). Live still needs the Delta plugin + gates.

## Polymarket

Public read only:

- Gamma `https://gamma-api.polymarket.com/markets` — discover
- CLOB `https://clob.polymarket.com/midpoint` + `/prices-history`

No wallet / CLOB API keys in this repo. **Dry/paper** records locally. **Live POLY is refused** until a signed CLOB client exists.

```
python src/data/backfill_5y.py --markets poly
# catalog → data/backfill/polymarket/catalog.json
# daily mids → data/backfill/polymarket/PM_*.csv
```

Add `PM_*` symbols to `MERIDIAN_SYMBOLS` after a catalog exists. Exchange `POLY`. Outcome prices are 0–1.

[Docs](https://docs.polymarket.com/api-reference/predictions/overview)
