# 5-year market backfill

**Window:** 2021-08-14 → 2026-08-15 (daily OHLCV)  
**Dir:** `data/backfill/`

| Venue | Source | Notes |
|-------|--------|--------|
| NSE cash + index | [jugaad-data](https://github.com/jugaad-py/jugaad-data) | Official NSE history. yfinance `.NS` if NSE hangs. |
| BSE cash + Sensex | yfinance `.BO` / `^BSESN` | Yahoo `.BO` is thin for many names → dual-list copy from NSE (`source=nse_dual_list`). |
| Crypto | yfinance | BTC/ETH/BNB/SOL/XRP/DOGE/ADA/AVAX/DOT/LINK |
| Forex | yfinance | INR crosses + majors. jugaad RBI is **current rates only**. |

jugaad-data has no BSE, crypto, or FX history.

## Refresh

```powershell
pip install jugaad-data yfinance
python src/data/backfill_5y.py --years 5
# if NSE blocks:
python src/data/backfill_5y.py --markets nse --nse-source yfinance
```

Skips existing files with ≥200 rows. `--force` overwrites.

## Combined files

- `nse_eq_daily.csv` / `nse_index_daily.csv`
- `bse_eq_daily.csv` / `bse_index_daily.csv`
- `crypto_daily.csv` / `forex_daily.csv`
- `manifest.json`

Schema: `date,open,high,low,close,volume,symbol,exchange,source,interval`

## NSE cleaning (required before research)

See `docs/NSE_DATA_CLEANING.md`. Split/bonus adjust, drop Muhurat + off-session bars, F&O roll calendar.

```powershell
python src/data/nse_clean.py
```

Output: `data/backfill/clean/`
