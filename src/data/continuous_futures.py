"""Continuous NSE F&O series.

Roll the front month on the monthly expiry (last Thursday through Aug 2025,
last Tuesday from Sep 2025; previous trading day if holiday).

Volume follows the live contract after the roll (no back-adjust on volume).
OHLC is Panama / ratio-adjusted backward so the stitch has no gap.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from nse_calendar import monthly_roll_dates, to_date


def roll_calendar(start: date, end: date) -> pd.DataFrame:
    rows = []
    for d in monthly_roll_dates(start, end):
        rows.append({
            "roll_date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "rule": "last_tuesday" if d >= date(2025, 9, 1) else "last_thursday",
        })
    return pd.DataFrame(rows)


def stitch_panama(front: pd.DataFrame, nxt: pd.DataFrame,
                  roll: date, date_col: str = "date",
                  price_cols: tuple[str, ...] = ("open", "high", "low", "close"),
                  volume_col: str = "volume") -> pd.DataFrame:
    """Use `front` until roll date inclusive, then `nxt`.

    Backward ratio = front_close / next_close on roll. Apply to all front
    bars so the series is continuous in price. Volume switches raw.
    """
    roll = to_date(roll)
    a = front.copy()
    b = nxt.copy()
    a[date_col] = pd.to_datetime(a[date_col]).dt.date
    b[date_col] = pd.to_datetime(b[date_col]).dt.date
    a_pre = a[a[date_col] <= roll].copy()
    b_post = b[b[date_col] > roll].copy()
    fc = a.loc[a[date_col] == roll, "close"]
    nc = b.loc[b[date_col] == roll, "close"]
    if len(fc) and len(nc) and float(nc.iloc[0]) != 0:
        ratio = float(fc.iloc[0]) / float(nc.iloc[0])
    else:
        ratio = 1.0
    for c in price_cols:
        if c in a_pre.columns:
            a_pre[c] = a_pre[c] * ratio
    a_pre["roll_ratio"] = ratio
    b_post["roll_ratio"] = 1.0
    out = pd.concat([a_pre, b_post], ignore_index=True).sort_values(date_col)
    if volume_col in out.columns:
        pass  # already the live contract's volume
    out["continuous"] = 1
    return out.reset_index(drop=True)
