"""Split-and-bonus adjustment only (no cash dividend).

NSE raw bhavcopy / jugaad CLOSE is unadjusted. A 1:1 bonus or 2-for-1 split
prints a gap that is not a loss. Walk backward from each ex-date and scale
all earlier OHLC by 1/ratio.

Yahoo `actions` stockSplits treats Indian bonus issues as splits.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

CACHE = Path(__file__).resolve().parents[2] / "data" / "backfill" / "corporate_actions"


def splits_from_yf(symbol: str, exchange: str = "NSE") -> pd.DataFrame:
    import yfinance as yf
    suffix = ".NS" if exchange.upper() in ("NSE", "NSE_INDEX") else ".BO"
    ticker = {"TATAMOTORS": "TMPV.NS"}.get(symbol, f"{symbol}{suffix}")
    s = yf.Ticker(ticker).splits
    if s is None or len(s) == 0:
        return pd.DataFrame(columns=["ex_date", "ratio", "symbol"])
    out = s.reset_index()
    out.columns = ["ex_date", "ratio"]
    out["ex_date"] = pd.to_datetime(out["ex_date"]).dt.tz_localize(None).dt.normalize()
    out["ratio"] = pd.to_numeric(out["ratio"], errors="coerce")
    out["symbol"] = symbol
    return out.dropna()


def load_or_fetch_splits(symbol: str, exchange: str = "NSE",
                         cache: Path | None = None) -> pd.DataFrame:
    dest = (cache or CACHE) / f"{symbol.replace('&', '_').replace('-', '_')}.csv"
    if dest.exists() and dest.stat().st_size > 0:
        return pd.read_csv(dest, parse_dates=["ex_date"])
    try:
        df = splits_from_yf(symbol, exchange)
    except Exception:
        df = pd.DataFrame(columns=["ex_date", "ratio", "symbol"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)
    return df


def adj_factor(dates: Iterable, splits: pd.DataFrame) -> pd.Series:
    """factor[t] = 1 / Π ratio for every split with ex_date > t.

    Latest bar stays at raw price (factor=1). Pre-split bars are scaled down.
    """
    idx = pd.to_datetime(pd.Series(list(dates))).dt.tz_localize(None).dt.normalize()
    fac = pd.Series(1.0, index=idx.index)
    if splits is None or splits.empty:
        return fac
    ev = splits.dropna(subset=["ex_date", "ratio"]).copy()
    ev = ev[ev["ratio"] > 0]
    ev["ex_date"] = pd.to_datetime(ev["ex_date"]).dt.tz_localize(None).dt.normalize()
    for _, row in ev.iterrows():
        fac.loc[idx < row["ex_date"]] = fac.loc[idx < row["ex_date"]] / float(row["ratio"])
    return fac


def apply_split_bonus(df: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["adj_factor"] = adj_factor(out["date"], splits).to_numpy()
    for col in ("open", "high", "low", "close"):
        if col in out.columns:
            out[f"adj_{col}"] = out[col] * out["adj_factor"]
    return out
