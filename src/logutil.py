"""Stdout-only log. OpenAlgo /python captures this."""
from __future__ import annotations

import sys
from datetime import datetime, timezone


def log(*args) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(ts, *args, flush=True, file=sys.stdout)
