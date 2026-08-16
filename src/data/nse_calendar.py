"""NSE session, holiday, Muhurat, and F&O expiry calendar.

Rules change over time. Each helper is date-aware.
Citations: docs/NSE_DATA_CLEANING.md
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# Equity continuous matching (user rule + NSE cash).
EQ_OPEN = time(9, 15)
EQ_CLOSE = time(15, 30)
# Pre-open order collection. Discard from execution bars.
PREOPEN_OPEN = time(9, 0)
PREOPEN_CLOSE = time(9, 15)
# Post-close / AMO. Discard.
POST_OPEN = time(15, 30)
POST_CLOSE = time(16, 0)

# CAS (cash F&O names) + F&O close extension. NSE live from 2026-08-03.
CAS_START = date(2026, 8, 3)
FO_CLOSE_BEFORE_CAS = time(15, 30)
FO_CLOSE_AFTER_CAS = time(15, 40)

# NSE circular FAOP68685 / SEBI standardisation.
# Contracts expiring on/before 2025-08-29 keep Thursday.
# New contracts from 2025-09-01 expire Tuesday.
EXPIRY_SWITCH = date(2025, 9, 1)
THURSDAY_LAST = date(2025, 8, 29)

# Diwali Laxmi Puja special live session. Times from exchange circulars / press.
# Regular 09:15–15:30 does NOT apply. Drop from MA/indicator series.
MUHURAT = {
    date(2021, 11, 4): (time(18, 0), time(19, 15)),
    date(2022, 10, 24): (time(18, 15), time(19, 15)),
    date(2023, 11, 12): (time(18, 15), time(19, 15)),
    date(2024, 11, 1): (time(18, 0), time(19, 0)),
    date(2025, 10, 21): (time(13, 45), time(14, 45)),
    date(2026, 11, 8): (time(13, 45), time(14, 45)),  # NSE holiday note; window TBD
}

# NSE cash/FO trading holidays (not weekends). Refresh yearly from nseindia.com/holidays.
# Muhurat days are holidays for the regular session and listed here too.
NSE_HOLIDAYS = {
    # 2021 (from Aug — our backfill start)
    date(2021, 8, 19), date(2021, 9, 10), date(2021, 10, 2), date(2021, 10, 15),
    date(2021, 11, 4), date(2021, 11, 5), date(2021, 11, 19), date(2021, 12, 25),
    # 2022
    date(2022, 1, 26), date(2022, 3, 1), date(2022, 3, 18), date(2022, 4, 14),
    date(2022, 4, 15), date(2022, 5, 3), date(2022, 8, 9), date(2022, 8, 15),
    date(2022, 8, 31), date(2022, 10, 5), date(2022, 10, 24), date(2022, 10, 26),
    date(2022, 11, 8), date(2022, 12, 25),
    # 2023
    date(2023, 1, 26), date(2023, 3, 7), date(2023, 3, 30), date(2023, 4, 4),
    date(2023, 4, 7), date(2023, 4, 14), date(2023, 5, 1), date(2023, 6, 29),
    date(2023, 8, 15), date(2023, 9, 19), date(2023, 10, 2), date(2023, 10, 24),
    date(2023, 11, 12), date(2023, 11, 14), date(2023, 11, 27), date(2023, 12, 25),
    # 2024
    date(2024, 1, 26), date(2024, 3, 8), date(2024, 3, 25), date(2024, 3, 29),
    date(2024, 4, 11), date(2024, 4, 17), date(2024, 5, 1), date(2024, 6, 17),
    date(2024, 7, 17), date(2024, 8, 15), date(2024, 10, 2), date(2024, 11, 1),
    date(2024, 11, 15), date(2024, 12, 25),
    # 2025
    date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31), date(2025, 4, 10),
    date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1), date(2025, 8, 15),
    date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 21), date(2025, 10, 22),
    date(2025, 11, 5), date(2025, 12, 25),
    # 2026 (NSE published list)
    date(2026, 1, 26), date(2026, 3, 3), date(2026, 3, 26), date(2026, 4, 3),
    date(2026, 4, 14), date(2026, 5, 1), date(2026, 5, 28), date(2026, 6, 26),
    date(2026, 9, 14), date(2026, 10, 2), date(2026, 10, 20), date(2026, 11, 8),
    date(2026, 11, 10), date(2026, 11, 24), date(2026, 12, 25),
}


def as_ist(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=IST)
    return ts.astimezone(IST)


def to_date(x) -> date:
    if isinstance(x, datetime):
        return as_ist(x).date()
    if hasattr(x, "date") and not isinstance(x, date):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def is_muhurat(d: date) -> bool:
    return to_date(d) in MUHURAT


def is_nse_holiday(d: date) -> bool:
    d = to_date(d)
    return is_weekend(d) or d in NSE_HOLIDAYS


def is_regular_trading_day(d: date) -> bool:
    """Full 09:15–15:30 cash session. Muhurat-only days are False."""
    d = to_date(d)
    if is_weekend(d) or d in NSE_HOLIDAYS:
        return False
    return True


def previous_trading_day(d: date) -> date:
    x = to_date(d) - timedelta(days=1)
    while is_nse_holiday(x):
        x -= timedelta(days=1)
    return x


def last_weekday(year: int, month: int, weekday: int) -> date:
    """weekday: Mon=0 … Sun=6. Last such day in the month."""
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def expiry_weekday(on: date) -> int:
    """NSE F&O expiry weekday in force for contracts *expiring* on this calendar."""
    on = to_date(on)
    # Existing Thursday contracts through 29 Aug 2025 EOD.
    if on <= THURSDAY_LAST:
        return 3  # Thursday
    return 1  # Tuesday from Sep 2025 (NSE FAOP68685 / SEBI)


def monthly_expiry(year: int, month: int) -> date:
    """Monthly F&O expiry, holiday-adjusted (previous trading day)."""
    wd = 1 if date(year, month, 1) >= EXPIRY_SWITCH else 3
    raw = last_weekday(year, month, wd)
    if is_nse_holiday(raw):
        return previous_trading_day(raw)
    return raw


def weekly_expiry(week_end: date) -> date:
    """Nifty weekly expiry in the week containing week_end (any day that week)."""
    d = to_date(week_end)
    monday = d - timedelta(days=d.weekday())
    wd = 3 if monday <= date(2025, 8, 25) else 1
    raw = monday + timedelta(days=wd)
    if is_nse_holiday(raw):
        return previous_trading_day(raw)
    return raw


def monthly_roll_dates(start: date, end: date) -> list[date]:
    out = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        e = monthly_expiry(y, m)
        if start <= e <= end:
            out.append(e)
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def fo_close(d: date) -> time:
    return FO_CLOSE_AFTER_CAS if to_date(d) >= CAS_START else FO_CLOSE_BEFORE_CAS


def classify_session(ts: datetime, segment: str = "EQ") -> str:
    """One of: pre_open | regular | muhurat | post_close | closed | fo_regular."""
    local = as_ist(ts)
    d = local.date()
    t = local.time()
    if is_muhurat(d):
        lo, hi = MUHURAT[d]
        if lo <= t <= hi:
            return "muhurat"
        return "closed"
    if is_nse_holiday(d):
        return "closed"
    if PREOPEN_OPEN <= t < EQ_OPEN:
        return "pre_open"
    if segment.upper() in ("FO", "FUT", "OPT", "F&O"):
        if EQ_OPEN <= t <= fo_close(d):
            return "fo_regular"
        if fo_close(d) < t <= POST_CLOSE:
            return "post_close"
        return "closed"
    if EQ_OPEN <= t <= EQ_CLOSE:
        return "regular"
    if EQ_CLOSE < t <= POST_CLOSE:
        return "post_close"
    return "closed"


def in_execution_window(ts: datetime, segment: str = "EQ") -> bool:
    """True only for continuous matching. Drops pre-open, post-close, Muhurat."""
    return classify_session(ts, segment) in ("regular", "fo_regular")


def session_type_for_daily(d: date) -> str:
    d = to_date(d)
    if is_muhurat(d):
        return "muhurat"
    if is_nse_holiday(d):
        return "holiday"
    return "regular"


def keep_daily_bar(d: date, keep_muhurat: bool = False) -> bool:
    d = to_date(d)
    if is_muhurat(d):
        return keep_muhurat
    return is_regular_trading_day(d)
