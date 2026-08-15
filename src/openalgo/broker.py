"""OpenAlgo helpers: analyzer preflight, ATR from Historify, telegram, reconcile."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from quotes import Quote


def ensure_analyzer(client, want: bool) -> dict:
    if client is None or not hasattr(client, "analyzerstatus"):
        return {"skipped": True}
    st = client.analyzerstatus() or {}
    on = bool(((st.get("data") or {}).get("analyze_mode")))
    if on != want and hasattr(client, "analyzertoggle"):
        return client.analyzertoggle(mode=want) or {"toggled": want}
    return st


def refuse_live_if_analyzer(client) -> None:
    if client is None or not hasattr(client, "analyzerstatus"):
        return
    st = client.analyzerstatus() or {}
    if bool(((st.get("data") or {}).get("analyze_mode"))):
        raise RuntimeError("refusing live: OpenAlgo analyzer is ON")


def atr_pct_from_history(client, symbol: str, exchange: str, n: int = 20) -> Optional[float]:
    if client is None or not hasattr(client, "history"):
        return None
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=5)
    try:
        df = client.history(
            symbol=symbol, exchange=exchange, interval="5m",
            start_date=str(start), end_date=str(end), source="db",
        )
    except Exception:
        return None
    if df is None or getattr(df, "empty", True) or len(df) < 5:
        return None
    tail = df.tail(n)
    prev = tail["close"].shift(1)
    tr = (tail["high"] - tail["low"]).to_numpy()
    # true range vs prior close when columns exist
    if prev.notna().any():
        a = (tail["high"] - tail["low"]).abs()
        b = (tail["high"] - prev).abs()
        c = (tail["low"] - prev).abs()
        tr = a.combine(b, max).combine(c, max)
    close = tail["close"].replace(0, float("nan"))
    ap = float((tr / close).dropna().mean())
    return ap if ap == ap else None  # NaN check


def patch_atr(q: Quote, atr_pct: Optional[float]) -> Quote:
    if not atr_pct or atr_pct <= 0:
        return q
    return q  # ATR applied in signal, not quote


def notify(client, username: str, msg: str) -> None:
    if not username or client is None or not hasattr(client, "telegram"):
        print("notify", msg)
        return
    try:
        client.telegram(username=username, message=msg)
    except Exception as e:
        print("telegram_fail", e)


def broker_qty(client, symbol: str, exchange: str, product: str) -> Optional[float]:
    if client is None or not hasattr(client, "openposition"):
        return None
    try:
        r = client.openposition(strategy="MeridianV4", symbol=symbol,
                                exchange=exchange, product=product)
        return float((r or {}).get("quantity") or 0)
    except Exception:
        return None
