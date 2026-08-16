"""NSE cleaning rules — offline, no network."""
from datetime import date, datetime
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "data"))

from corporate_actions import adj_factor, apply_split_bonus  # noqa: E402
from continuous_futures import roll_calendar, stitch_panama  # noqa: E402
from nse_clean import repair_session_date  # noqa: E402
from nse_calendar import (  # noqa: E402
    classify_session,
    in_execution_window,
    keep_daily_bar,
    monthly_expiry,
    weekly_expiry,
)


def test_jugaad_sunday_is_monday_session():
    raw = pd.DataFrame({
        "date": [pd.Timestamp("2021-08-15")],  # Sunday
        "close": [1.0],
        "source": ["jugaad-data"],
    })
    out = repair_session_date(raw)
    assert out["date"].iloc[0].date() == date(2021, 8, 16)


def test_regular_session_kept_preopen_dropped():
    open_bar = datetime(2026, 8, 14, 9, 15, 0)  # naive, treated as IST
    pre = datetime(2026, 8, 14, 9, 5, 0)
    post = datetime(2026, 8, 14, 15, 45, 0)
    assert classify_session(open_bar) == "regular"
    assert classify_session(pre) == "pre_open"
    assert classify_session(post) == "post_close"
    assert in_execution_window(open_bar)
    assert not in_execution_window(pre)
    assert not in_execution_window(post)


def test_muhurat_2025_afternoon_not_regular():
    # 21 Oct 2025 13:45–14:45 IST — inside clock but NOT 09:15–15:30 regular series
    inside = datetime(2025, 10, 21, 14, 0, 0)
    assert classify_session(inside) == "muhurat"
    assert not in_execution_window(inside)
    assert not keep_daily_bar(date(2025, 10, 21))
    assert keep_daily_bar(date(2025, 10, 21), keep_muhurat=True)


def test_expiry_thursday_then_tuesday():
    assert monthly_expiry(2024, 8) == date(2024, 8, 29)  # last Thursday
    assert monthly_expiry(2025, 8) == date(2025, 8, 28)  # last Thursday
    assert monthly_expiry(2025, 9) == date(2025, 9, 30)  # last Tuesday (ICICI / NSE)
    assert monthly_expiry(2025, 10) == date(2025, 10, 28)  # last Tuesday


def test_expiry_holiday_shifts_previous_trading_day():
    # 1 May 2025 is Thursday + Maharashtra Day → weekly rolls to 30 Apr
    assert weekly_expiry(date(2025, 5, 1)) == date(2025, 4, 30)


def test_split_bonus_scales_history_not_latest():
    dates = pd.to_datetime(["2022-01-03", "2022-06-01", "2022-06-02"])
    splits = pd.DataFrame({"ex_date": [pd.Timestamp("2022-06-01")], "ratio": [2.0]})
    fac = adj_factor(dates, splits)
    assert abs(fac.iloc[0] - 0.5) < 1e-12
    assert abs(fac.iloc[1] - 1.0) < 1e-12
    raw = pd.DataFrame({
        "date": dates, "open": [200.0, 100.0, 101.0], "high": [200, 100, 101],
        "low": [200, 100, 101], "close": [200.0, 100.0, 101.0],
    })
    out = apply_split_bonus(raw, splits)
    assert abs(out["adj_close"].iloc[0] - 100.0) < 1e-9
    assert abs(out["adj_close"].iloc[-1] - 101.0) < 1e-9


def test_roll_calendar_switches_rule():
    cal = roll_calendar(date(2025, 7, 1), date(2025, 10, 31))
    rules = dict(zip(cal["roll_date"], cal["rule"]))
    assert rules["2025-07-31"] == "last_thursday"
    assert rules["2025-08-28"] == "last_thursday"
    assert rules["2025-09-30"] == "last_tuesday"


def test_panama_stitch_no_gap_volume_follows_live():
    front = pd.DataFrame({
        "date": ["2025-09-29", "2025-09-30"],
        "close": [100.0, 110.0], "open": [100, 110], "high": [100, 110],
        "low": [100, 110], "volume": [10, 10],
    })
    nxt = pd.DataFrame({
        "date": ["2025-09-30", "2025-10-01"],
        "close": [55.0, 56.0], "open": [55, 56], "high": [55, 56],
        "low": [55, 56], "volume": [99, 80],
    })
    out = stitch_panama(front, nxt, date(2025, 9, 30))
    # front 100 scaled by 110/55 = 2 → 200; roll close 110*2=220; next 56
    assert abs(out.loc[out["date"] == date(2025, 9, 29), "close"].iloc[0] - 200.0) < 1e-9
    assert int(out.loc[out["date"] == date(2025, 10, 1), "volume"].iloc[0]) == 80
