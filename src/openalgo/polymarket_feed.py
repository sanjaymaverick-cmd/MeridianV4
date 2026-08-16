"""QuoteFeed for Polymarket YES tokens. Public CLOB mid. Not for live CLOB orders."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from quotes import Quote, QuoteFeed

_DATA = Path(__file__).resolve().parents[1] / "data"
if str(_DATA) not in sys.path:
    sys.path.insert(0, str(_DATA))

from polymarket import load_catalog, midpoint  # noqa: E402


class PolymarketFeed(QuoteFeed):
    def __init__(self, catalog: list[dict] | None = None):
        self.catalog = catalog if catalog is not None else load_catalog()
        self.by_sym = {m["symbol"]: m for m in self.catalog if m.get("symbol")}

    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for sym, ex in pairs:
            if ex not in ("POLY", "POLYMARKET") and sym not in self.by_sym:
                continue
            meta = self.by_sym.get(sym)
            if not meta:
                continue
            px = midpoint(meta["token_id"])
            if px is None:
                px = float(meta.get("price") or 0.0)
            if px <= 0:
                continue
            out[sym] = Quote(
                symbol=sym, exchange="POLY",
                ltp=px, open=px, high=px, low=px, prev_close=px, volume=0.0,
            )
        return out
