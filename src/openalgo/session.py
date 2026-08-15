"""India cash session + crypto clock. Times in IST unless noted."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)
NSE_FLATTEN = time(15, 15)


def to_ist(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(IST)


def minutes_since_midnight(now: datetime, exchange: str = "NSE") -> float:
    if exchange == "DELTA":
        u = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
        return u.hour * 60 + u.minute + u.second / 60.0
    local = to_ist(now)
    return local.hour * 60 + local.minute + local.second / 60.0


def minutes_to_eod(now: datetime, exchange: str = "NSE") -> float:
    if exchange == "DELTA":
        return 999.0  # no cash EOD
    local = to_ist(now)
    flatten = local.replace(hour=NSE_FLATTEN.hour, minute=NSE_FLATTEN.minute, second=0, microsecond=0)
    return (flatten - local).total_seconds() / 60.0


def nse_open(now: datetime) -> bool:
    local = to_ist(now)
    if local.weekday() >= 5:
        return False
    t = local.time()
    return NSE_OPEN <= t <= NSE_CLOSE
