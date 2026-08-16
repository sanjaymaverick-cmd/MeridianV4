#!/usr/bin/env python3
"""5-year daily OHLCV backfill.

NSE stocks + indices: jugaad-data (https://github.com/jugaad-py/jugaad-data)
BSE / crypto / forex: yfinance (jugaad-data has no BSE/crypto/FX history)

Usage:
  python src/data/backfill_5y.py
  python src/data/backfill_5y.py --markets nse,crypto
  python src/data/backfill_5y.py --years 5 --force
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from universe import BSE_EQ, BSE_INDEX, CRYPTO, FOREX, NSE_EQ, NSE_INDEX  # noqa: E402

OUT = ROOT / "data" / "backfill"
COLS = ["date", "open", "high", "low", "close", "volume", "symbol", "exchange", "source", "interval"]


def _ist_session_date(s: pd.Series) -> pd.Series:
    """Map NSE timestamps onto the IST trading date.

    Midnight IST is often stored as 18:30 UTC the prior day. If more than
    half the bars fall on Sat/Sun, shift +1 day (jugaad/nsepy pattern).
    """
    dt = pd.to_datetime(s, utc=True)
    ist = dt.dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    if (ist.dt.weekday >= 5).mean() > 0.3:
        ist = ist + pd.Timedelta(days=1)
    return ist


def _norm(df: pd.DataFrame, symbol: str, exchange: str, source: str) -> pd.DataFrame:
    out = pd.DataFrame({
        "date": _ist_session_date(df["date"]),
        "open": pd.to_numeric(df["open"], errors="coerce"),
        "high": pd.to_numeric(df["high"], errors="coerce"),
        "low": pd.to_numeric(df["low"], errors="coerce"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
        "volume": pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0),
        "symbol": symbol,
        "exchange": exchange,
        "source": source,
        "interval": "1d",
    })
    out = out.dropna(subset=["date", "close"])
    out = out[out["close"] > 0]
    return out.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def _save(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df[COLS].to_csv(path, index=False)
    return path


def _skip(path: Path, force: bool, min_rows: int = 200) -> bool:
    if force or not path.exists() or path.stat().st_size == 0:
        return False
    try:
        n = sum(1 for _ in open(path, encoding="utf-8")) - 1
    except OSError:
        return False
    return n >= min_rows


def fetch_nse_eq(symbol: str, start: date, end: date) -> pd.DataFrame:
    from jugaad_data.nse import stock_df
    raw = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
    if raw is None or raw.empty:
        raise RuntimeError("jugaad empty")
    return _norm(
        pd.DataFrame({
            "date": raw["DATE"],
            "open": raw["OPEN"],
            "high": raw["HIGH"],
            "low": raw["LOW"],
            "close": raw["CLOSE"],
            "volume": raw["VOLUME"],
        }),
        symbol, "NSE", "jugaad-data",
    )


def fetch_nse_eq_safe(symbol: str, start: date, end: date) -> pd.DataFrame:
    """jugaad-data first (60s); yfinance .NS if NSE hangs or returns empty."""
    try:
        return _call(lambda: fetch_nse_eq(symbol, start, end), 60.0)
    except Exception as e:
        print(f"    jugaad fallback {symbol}: {e}", flush=True)
        return fetch_yf(f"{symbol}.NS", symbol, "NSE", start, end)


NSE_YF_ALIAS = {
    "TATAMOTORS": "TMPV.NS",  # renamed 2025
}

NSE_INDEX_YF = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY FINANCIAL SERVICES": "NIFTY_FIN_SERVICE.NS",
    "NIFTY MIDCAP 50": "NIFTY_MIDCAP_50.NS",
    "NIFTY NEXT 50": "NIFTYNXT50.NS",
}


def fetch_nse_index(name: str, start: date, end: date) -> pd.DataFrame:
    from jugaad_data.nse import index_df
    raw = index_df(name, start, end)
    if raw is None or raw.empty:
        raise RuntimeError("jugaad index empty")
    dcol = "HistoricalDate" if "HistoricalDate" in raw.columns else "DATE"
    return _norm(
        pd.DataFrame({
            "date": raw[dcol],
            "open": raw["OPEN"],
            "high": raw["HIGH"],
            "low": raw["LOW"],
            "close": raw["CLOSE"],
            "volume": 0,
        }),
        name.replace(" ", "_"), "NSE_INDEX", "jugaad-data",
    )


def fetch_nse_index_safe(name: str, start: date, end: date) -> pd.DataFrame:
    try:
        return _call(lambda: fetch_nse_index(name, start, end), 45.0)
    except Exception as e:
        ticker = NSE_INDEX_YF.get(name)
        print(f"    jugaad index fallback {name}: {e}", flush=True)
        if not ticker:
            raise
        return fetch_yf(ticker, name.replace(" ", "_"), "NSE_INDEX", start, end)


def fetch_yf(ticker: str, symbol: str, exchange: str, start: date, end: date) -> pd.DataFrame:
    import yfinance as yf
    # yfinance end is exclusive
    hist = yf.Ticker(ticker).history(start=str(start), end=str(end + timedelta(days=1)), interval="1d", auto_adjust=False)
    if hist is None or hist.empty:
        return pd.DataFrame(columns=COLS)
    hist = hist.reset_index()
    dcol = "Date" if "Date" in hist.columns else hist.columns[0]
    return _norm(
        pd.DataFrame({
            "date": hist[dcol],
            "open": hist["Open"],
            "high": hist["High"],
            "low": hist["Low"],
            "close": hist["Close"],
            "volume": hist["Volume"] if "Volume" in hist.columns else 0,
        }),
        symbol, exchange, "yfinance",
    )


def _call(fn, timeout_s: float):
    if timeout_s <= 0:
        return fn()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        return fut.result(timeout=timeout_s)


def _run_one(label: str, dest: Path, fn, force: bool, sleep_s: float, stats: dict,
             timeout_s: float = 90.0) -> None:
    if _skip(dest, force):
        stats["skipped"] += 1
        print(f"  skip {label}", flush=True)
        return
    print(f"  fetch {label} ...", flush=True)
    try:
        df = _call(fn, timeout_s)
    except FutTimeout:
        stats["fail"] += 1
        stats["errors"].append({"symbol": label, "error": f"timeout {timeout_s}s"})
        print(f"  FAIL {label}: timeout {timeout_s}s", flush=True)
        return
    except Exception as e:
        stats["fail"] += 1
        stats["errors"].append({"symbol": label, "error": str(e)})
        print(f"  FAIL {label}: {e}", flush=True)
        traceback.print_exc()
        return
    if df is None or df.empty:
        stats["fail"] += 1
        stats["errors"].append({"symbol": label, "error": "empty"})
        print(f"  empty {label}", flush=True)
        return
    _save(df, dest)
    stats["ok"] += 1
    stats["rows"] += int(len(df))
    print(f"  ok   {label} n={len(df)} {df['date'].min().date()}→{df['date'].max().date()}", flush=True)
    if sleep_s:
        time.sleep(sleep_s)


def combine(folder: Path, dest: Path) -> int:
    frames = []
    for p in sorted(folder.glob("*.csv")):
        if p.name.startswith("_"):
            continue
        frames.append(pd.read_csv(p, parse_dates=["date"]))
    if not frames:
        return 0
    out = pd.concat(frames, ignore_index=True).sort_values(["symbol", "date"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    return len(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--markets", default="nse,bse,crypto,forex")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.6, help="pause between NSE calls")
    ap.add_argument("--nse-source", choices=("jugaad", "yfinance"), default="jugaad")
    ap.add_argument("--clean", action="store_true", help="run NSE cleaning after download")
    args = ap.parse_args()

    end = date.today()
    start = end - timedelta(days=365 * args.years + 2)
    markets = {m.strip().lower() for m in args.markets.split(",") if m.strip()}
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {"ok": 0, "fail": 0, "skipped": 0, "rows": 0, "errors": []}

    print(f"backfill {start} → {end} markets={sorted(markets)}")

    if "nse" in markets:
        print("=== NSE EQ (jugaad-data) ===")
        for sym in NSE_EQ:
            dest = OUT / "nse" / "eq" / f"{sym.replace('&', '_').replace('-', '_')}.csv"
            if args.nse_source == "yfinance":
                fn = lambda s=sym: fetch_yf(NSE_YF_ALIAS.get(s, f"{s}.NS"), s, "NSE", start, end)
            else:
                fn = lambda s=sym: fetch_nse_eq_safe(s, start, end)
            _run_one(f"NSE:{sym}", dest, fn, args.force, args.sleep, stats, timeout_s=120.0)
        print("=== NSE INDEX ===")
        for name in NSE_INDEX:
            slug = name.replace(" ", "_")
            dest = OUT / "nse" / "index" / f"{slug}.csv"
            if args.nse_source == "yfinance":
                ticker = NSE_INDEX_YF.get(name, f"{slug}.NS")
                fn = lambda t=ticker, n=name: fetch_yf(t, n.replace(" ", "_"), "NSE_INDEX", start, end)
            else:
                fn = lambda n=name: fetch_nse_index_safe(n, start, end)
            _run_one(f"NSEIDX:{name}", dest, fn, args.force, args.sleep, stats, timeout_s=90.0)

    if "bse" in markets:
        print("=== BSE (yfinance .BO) ===")
        for sym in BSE_EQ:
            dest = OUT / "bse" / "eq" / f"{sym.replace('&', '_').replace('-', '_')}.csv"
            _run_one(f"BSE:{sym}", dest,
                     lambda s=sym: fetch_yf(f"{s}.BO", s, "BSE", start, end),
                     args.force, 0.15, stats)
        for name, ticker in BSE_INDEX:
            dest = OUT / "bse" / "index" / f"{name}.csv"
            _run_one(f"BSEIDX:{name}", dest,
                     lambda t=ticker, n=name: fetch_yf(t, n, "BSE_INDEX", start, end),
                     args.force, 0.15, stats)

    if "crypto" in markets:
        print("=== CRYPTO (yfinance) ===")
        for t in CRYPTO:
            dest = OUT / "crypto" / f"{t}.csv"
            _run_one(f"CRYPTO:{t}", dest,
                     lambda x=t: fetch_yf(x, x, "CRYPTO", start, end),
                     args.force, 0.1, stats)

    if "forex" in markets:
        print("=== FOREX (yfinance) ===")
        for t in FOREX:
            slug = t.replace("=", "_")
            dest = OUT / "forex" / f"{slug}.csv"
            _run_one(f"FX:{t}", dest,
                     lambda x=t: fetch_yf(x, x, "FOREX", start, end),
                     args.force, 0.1, stats)

    combined = {}
    for venue, folder in (
        ("nse_eq", OUT / "nse" / "eq"),
        ("nse_index", OUT / "nse" / "index"),
        ("bse_eq", OUT / "bse" / "eq"),
        ("bse_index", OUT / "bse" / "index"),
        ("crypto", OUT / "crypto"),
        ("forex", OUT / "forex"),
    ):
        if folder.exists():
            n = combine(folder, OUT / f"{venue}_daily.csv")
            combined[venue] = n
            print(f"combined {venue} rows={n}")

    manifest = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": str(start),
        "to": str(end),
        "years": args.years,
        "markets": sorted(markets),
        "sources": {
            "nse": "jugaad-data (https://github.com/jugaad-py/jugaad-data)",
            "bse": "yfinance (.BO / ^BSESN)",
            "crypto": "yfinance",
            "forex": "yfinance (jugaad RBI is current-rates only)",
        },
        "stats": {k: stats[k] for k in ("ok", "fail", "skipped", "rows")},
        "errors": stats["errors"],
        "combined_rows": combined,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["stats"], indent=2))
    print("manifest →", OUT / "manifest.json")
    if args.clean:
        from nse_clean import run as clean_run
        clean_run(keep_muhurat=False, fetch_splits=True)
    return 0 if stats["fail"] == 0 or stats["ok"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
