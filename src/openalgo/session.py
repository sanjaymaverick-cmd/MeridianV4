"""India cash / NFO session + crypto clock. Times in IST unless noted."""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)
NSE_FLATTEN = time(15, 15)
NFO_EXCHANGES = {"NFO", "BFO", "NSE_FO"}

_DATA = Path(__file__).resolve().parents[1] / "data"
if str(_DATA) not in sys.path:
    sys.path.insert(0, str(_DATA))


def to_ist(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(IST)


def _holiday(d) -> bool:
    try:
        from nse_calendar import is_nse_holiday
        return is_nse_holiday(d)
    except ImportError:
        return d.weekday() >= 5


def minutes_since_midnight(now: datetime, exchange: str = "NSE") -> float:
    if exchange == "DELTA":
        u = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
        return u.hour * 60 + u.minute + u.second / 60.0
    local = to_ist(now)
    return local.hour * 60 + local.minute + local.second / 60.0


def minutes_to_eod(now: datetime, exchange: str = "NSE") -> float:
    if exchange == "DELTA":
        return 999.0
    local = to_ist(now)
    flatten = local.replace(hour=NSE_FLATTEN.hour, minute=NSE_FLATTEN.minute, second=0, microsecond=0)
    return (flatten - local).total_seconds() / 60.0


def nse_open(now: datetime) -> bool:
    local = to_ist(now)
    if _holiday(local.date()):
        return False
    t = local.time()
    return NSE_OPEN <= t <= NSE_CLOSE
