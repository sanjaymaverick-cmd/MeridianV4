# NSE critical data-cleaning rules

Apply these **before** indicators, meta-labels, or F&O research. Encoded in `src/data/nse_calendar.py`, `corporate_actions.py`, `continuous_futures.py`, `nse_clean.py`.

Rules change. Recheck NSE circulars when the calendar year rolls.

## 1. Corporate actions — split and bonus only

**Why:** Unadjusted NSE bhavcopy / jugaad `CLOSE` gaps down on a 1:1 bonus or N-for-1 split. That is not a loss. Leaving it in warps returns, ATR, and meta-labels.

**Rule:** Keep raw OHLC. Add `adj_*` scaled so the latest bar equals raw. For every split/bonus with `ex_date > t`:

`adj_price[t] = raw[t] / Π ratio(ex > t)`

Cash dividends are **not** stripped (this is not total-return). Yahoo `stockSplits` treats Indian bonus issues as splits — we cache those files under `data/backfill/corporate_actions/`.

jugaad-data is unadjusted. yfinance `auto_adjust=True` mixes dividends in; do not use it as the sole adj source.

## 1b. Session date (jugaad UTC shift)

jugaad-data / nsepy often emit IST midnight as `18:30` UTC the **previous** calendar day. Monday's bar lands on Sunday; Friday nearly vanishes. The cleaner adds one day for `source in {jugaad-data, nse_dual_list}` before holiday/Muhurat filters. yfinance dates are left alone.

## 2. Market-hour filter — 09:15–15:30 IST

NSE cash continuous matching is **09:15–15:30 IST**.  
[Market timings](https://www.nseindia.com/static/market-data/market-timings)

| Session | Window (IST) | Keep in execution series? |
|---------|--------------|---------------------------|
| Block deal | 08:45–09:00 | No |
| Pre-open | 09:00–09:08 (+ match to 09:15) | No — opening auction, not continuous |
| Continuous EQ | **09:15–15:30** | **Yes** |
| CAS (F&O cash names, from 3 Aug 2026) | 15:15–15:35 | Close discovery — do not treat as continuous ticks |
| Post-close | ~15:30/15:40–16:00 | No |
| T+0 | 09:15–13:30 | Separate series; never mix into T+1 |

Intraday: `in_execution_window(ts)` must be true.  
Daily: one official EQ bar is the 09:15–15:30 session. Still drop **Muhurat-only** days (below).

**F&O clock change:** equity F&O closed 15:30 until CAS; from **2026-08-03** F&O runs to **15:40** to sit after CAS ([NSE CAS](https://www.nseindia.com/static/products-services/closing-auction-session)). `fo_close(d)` is date-aware.

## 3. Rollover — continuous futures

**Through 29 Aug 2025 EOD:** monthly (and Nifty weekly) expiry = **last Thursday** of the period; if holiday, **previous trading day**.

**From 1 Sep 2025** (new contracts): NSE index + stock F&O expiry = **Tuesday** (monthly = last Tuesday). BSE moved the other way (Thursday).  
Source: NSE circular [FAOP68685](https://nsearchives.nseindia.com/content/circulars/FAOP68685.pdf) via [ICICI note](https://www.icicidirect.com/futures-and-options/articles/revised-expiry-days-for-nse-futures-and-options). A March 2025 “Monday” headline was **not** the implemented rule.

**Stitch:** on `monthly_expiry(y, m)` switch front → next. Panama-adjust OHLC backward (`front_close / next_close` on roll). **Volume stays with the live contract** after the roll.

Calendar: `data/backfill/clean/nse_fo_roll_calendar.csv`.

## 4. Special sessions that are not regular hours

### Muhurat (Diwali Laxmi Puja)

One-hour **special live** session. Regular 09:15–15:30 is **closed**. Including that bar in daily MAs is the same class of error as keeping pre-open ticks.

| Date | Window (IST) |
|------|----------------|
| 2021-11-04 | 18:00–19:15 |
| 2022-10-24 | 18:15–19:15 |
| 2023-11-12 | 18:15–19:15 |
| 2024-11-01 | 18:00–19:00 |
| 2025-10-21 | **13:45–14:45** (afternoon; not evening) |
| 2026-11-08 | TBA — NSE holiday list already marks Muhurat that day |

Default: **drop** from `keep_regular`. `--keep-muhurat` to retain tagged.

### Other structural exceptions

- **Weekends + published NSE holidays** — not trading days. Holiday list in `nse_calendar.NSE_HOLIDAYS`; refresh each January from [NSE holidays](https://www.nseindia.com/resources/exchange-communication-holidays).
- **Budget day** — cash hours have been the normal 09:15–15:30 in this 5y window. Do not apply an old late-open filter.
- **Mock / special live drills** — discard (`session_type=closed` unless listed).
- **T+0** — 09:15–13:30; own series.
- **Settlement vs trading holiday** — only **trading** holidays close the book. Settlement-only days still get a 09:15–15:30 bar.

## Run

```powershell
python src/data/nse_clean.py                  # drop Muhurat, fetch splits
python src/data/nse_clean.py --keep-muhurat
python src/data/nse_clean.py --no-fetch-splits
```

Writes `data/backfill/clean/{nse_eq,nse_index,bse_eq}_daily.csv` plus the F&O roll calendar.

Use **`adj_close` / `adj_high` / `adj_low` / `adj_open`** for research. Keep raw for audit.
