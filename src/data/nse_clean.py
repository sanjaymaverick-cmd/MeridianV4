#!/usr/bin/env python3
"""Apply NSE critical cleaning rules to the 5y backfill.

1. Split-and-bonus adjust (raw OHLC kept; adj_* added).
2. Drop bars outside the 09:15–15:30 IST equity window (intraday)
   and Muhurat-only days from the regular daily series.
3. Write F&O monthly roll calendar (Thursday → Tuesday after Aug 2025).

Usage:
  python src/data/nse_clean.py
  python src/data/nse_clean.py --keep-muhurat --no-fetch-splits
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # src/data → repo root
sys.path.insert(0, str(HERE))

from corporate_actions import apply_split_bonus, load_or_fetch_splits  # noqa: E402
from continuous_futures import roll_calendar  # noqa: E402
from nse_calendar import (  # noqa: E402
    keep_daily_bar,
    monthly_expiry,
    session_type_for_daily,
    to_date,
)

RAW = ROOT / "data" / "backfill"
CLEAN = RAW / "clean"


JUGAAD_SOURCES = {"jugaad-data", "nse_dual_list"}


def repair_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """jugaad stores IST midnight as UTC 18:30 → calendar date is -1 day."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    if "source" in out.columns:
        m = out["source"].isin(JUGAAD_SOURCES)
        out.loc[m, "date"] = out.loc[m, "date"] + pd.Timedelta(days=1)
    return out


def _tag_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dts = pd.to_datetime(out["date"]).dt.date
    out["session_type"] = [session_type_for_daily(d) for d in dts]
    out["is_muhurat"] = (out["session_type"] == "muhurat").astype(int)
    out["is_expiry_monthly"] = [
        1 if d == monthly_expiry(d.year, d.month) else 0 for d in dts
    ]
    return out


def clean_daily(df: pd.DataFrame, *, keep_muhurat: bool,
                fetch_splits: bool) -> pd.DataFrame:
    df = repair_session_date(df)
    df = _tag_calendar(df)
    dts = pd.to_datetime(df["date"]).dt.date
    df["keep_regular"] = [int(keep_daily_bar(d, keep_muhurat)) for d in dts]
    kept = df[df["keep_regular"] == 1].copy()

    parts = []
    for (sym, ex), g in kept.groupby(["symbol", "exchange"], sort=False):
        if fetch_splits and str(ex).upper() in ("NSE", "BSE"):
            splits = load_or_fetch_splits(str(sym), str(ex))
        else:
            splits = pd.DataFrame(columns=["ex_date", "ratio", "symbol"])
        parts.append(apply_split_bonus(g, splits))
    if not parts:
        return kept
    return pd.concat(parts, ignore_index=True).sort_values(["symbol", "date"])


def run(keep_muhurat: bool = False, fetch_splits: bool = True) -> dict:
    CLEAN.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name in ("nse_eq_daily.csv", "nse_index_daily.csv", "bse_eq_daily.csv"):
        src = RAW / name
        if not src.exists():
            stats[name] = {"skipped": True}
            continue
        raw = pd.read_csv(src, parse_dates=["date"])
        out = clean_daily(raw, keep_muhurat=keep_muhurat, fetch_splits=fetch_splits)
        dest = CLEAN / name
        out.to_csv(dest, index=False)
        dropped = int(len(raw) - len(out))
        stats[name] = {
            "in": int(len(raw)), "out": int(len(out)), "dropped": dropped,
            "muhurat_in": int((pd.to_datetime(raw["date"]).dt.date.map(
                lambda d: session_type_for_daily(d) == "muhurat")).sum()),
        }
        print(f"{name}: {len(raw)} → {len(out)} (dropped {dropped})")

    start, end = date(2021, 8, 14), date(2026, 12, 31)
    rolls = roll_calendar(start, end)
    rolls.to_csv(CLEAN / "nse_fo_roll_calendar.csv", index=False)
    stats["fo_rolls"] = int(len(rolls))
    print(f"fo roll dates: {len(rolls)}")

    man = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "keep_muhurat": keep_muhurat,
        "fetch_splits": fetch_splits,
        "stats": stats,
        "rules": [
            "split_bonus_adjusted",
            "drop_outside_0915_1530_and_muhurat",
            "fo_roll_last_thursday_until_2025-08 then last_tuesday",
        ],
    }
    (CLEAN / "manifest.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    return man


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-muhurat", action="store_true")
    ap.add_argument("--no-fetch-splits", action="store_true")
    args = ap.parse_args()
    run(keep_muhurat=args.keep_muhurat, fetch_splits=not args.no_fetch_splits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
