"""Quote adapter. Dry book is default; paper uses OpenAlgo quotes/multiquotes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional


@dataclass
class Quote:
    symbol: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float = 0.0


def _parse_oa(symbol: str, exchange: str, data: Mapping) -> Quote:
    ltp = float(data.get("ltp") or data.get("close") or 0.0)
    return Quote(
        symbol=symbol,
        exchange=exchange,
        ltp=ltp,
        open=float(data.get("open") or ltp),
        high=float(data.get("high") or ltp),
        low=float(data.get("low") or ltp),
        prev_close=float(data.get("prev_close") or data.get("close") or ltp),
        volume=float(data.get("volume") or 0.0),
    )


class QuoteFeed:
    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        raise NotImplementedError


class DryFeed(QuoteFeed):
    """In-memory book. Tests / hosted dry loop push ticks here."""

    def __init__(self, book: Optional[dict[str, Quote]] = None):
        self.book: dict[str, Quote] = dict(book or {})

    def push(self, q: Quote) -> None:
        self.book[q.symbol] = q

    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        out = {}
        for sym, _ex in pairs:
            if sym in self.book:
                out[sym] = self.book[sym]
        return out


class OpenAlgoFeed(QuoteFeed):
    def __init__(self, client):
        self.client = client

    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        pairs = list(pairs)
        out: dict[str, Quote] = {}
        if hasattr(self.client, "multiquotes"):
            resp = self.client.multiquotes(
                symbols=[{"symbol": s, "exchange": e} for s, e in pairs]
            )
            rows = (resp or {}).get("results") or []
            for row in rows:
                if (row or {}).get("data"):
                    q = _parse_oa(row["symbol"], row.get("exchange", ""), row["data"])
                    out[q.symbol] = q
            return out
        for sym, ex in pairs:
            resp = self.client.quotes(symbol=sym, exchange=ex)
            data = (resp or {}).get("data") or {}
            if data:
                out[sym] = _parse_oa(sym, ex, data)
        return out
