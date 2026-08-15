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


YF_TICKER = {
    "INFY": "INFY.NS", "HCLTECH": "HCLTECH.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "M&M": "M&M.NS", "BAJAJFINSV": "BAJAJFINSV.NS", "GRASIM": "GRASIM.NS",
    "NESTLEIND": "NESTLEIND.NS", "BRITANNIA": "BRITANNIA.NS",
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "SBIN": "SBIN.NS",
    "BNBUSDT": "BNB-USD",
}


class YFinanceFeed(QuoteFeed):
    """Paper-train LTP when Kite Personal denies quotes. Not for live."""

    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        try:
            import yfinance as yf
        except ImportError:
            return {}
        out: dict[str, Quote] = {}
        for sym, ex in pairs:
            ticker = YF_TICKER.get(sym)
            if not ticker:
                continue
            try:
                h = yf.Ticker(ticker).history(period="5d", interval="1d")
            except Exception:
                continue
            if h is None or len(h) == 0:
                continue
            last = h.iloc[-1]
            px = float(last["Close"])
            out[sym] = Quote(
                symbol=sym, exchange=ex, ltp=px,
                open=float(last.get("Open", px)),
                high=float(last.get("High", px)),
                low=float(last.get("Low", px)),
                prev_close=float(h["Close"].iloc[-2]) if len(h) > 1 else px,
                volume=float(last.get("Volume", 0) or 0),
            )
        return out


class FallbackFeed(QuoteFeed):
    def __init__(self, primary: QuoteFeed, secondary: QuoteFeed):
        self.primary = primary
        self.secondary = secondary

    def fetch(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Quote]:
        pairs = list(pairs)
        got: dict[str, Quote] = {}
        try:
            got = self.primary.fetch(pairs) or {}
        except Exception:
            got = {}
        missing = [(s, e) for s, e in pairs if s not in got]
        if missing:
            try:
                got.update(self.secondary.fetch(missing) or {})
            except Exception:
                pass
        return got


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
