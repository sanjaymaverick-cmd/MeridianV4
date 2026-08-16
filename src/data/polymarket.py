"""Polymarket public read path. No API key.

Gamma: https://gamma-api.polymarket.com  (events / markets)
CLOB:  https://clob.polymarket.com       (mid, prices-history)

Trading (signed CLOB orders) is not implemented — paper/dry only.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
CATALOG = Path(__file__).resolve().parents[2] / "data" / "backfill" / "polymarket" / "catalog.json"


def _get(url: str, params: dict | None = None, timeout: float = 30.0) -> Any:
    if params:
        url = url + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": "MeridianV4/0.4", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _parse_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return [val]
    return []


def list_markets(limit: int = 30, closed: bool = False) -> list[dict]:
    """Active CLOB markets, highest 24h volume first."""
    rows = _get(f"{GAMMA}/markets", {
        "limit": int(limit),
        "closed": str(closed).lower(),
        "order": "volume24hr",
        "ascending": "false",
    })
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("markets") or []
    out = []
    for m in rows or []:
        tokens = _parse_list(m.get("clobTokenIds"))
        prices = _parse_list(m.get("outcomePrices"))
        outcomes = _parse_list(m.get("outcomes")) or ["Yes", "No"]
        if not tokens:
            continue
        yes_px = 0.0
        try:
            yes_px = float(prices[0]) if prices else 0.0
        except (TypeError, ValueError, IndexError):
            yes_px = 0.0
        slug = str(m.get("slug") or m.get("conditionId") or tokens[0])[:48]
        out.append({
            "symbol": "PM_" + "".join(c if c.isalnum() else "_" for c in slug)[:28].upper(),
            "slug": m.get("slug"),
            "question": m.get("question"),
            "token_id": str(tokens[0]),
            "outcome": str(outcomes[0]) if outcomes else "Yes",
            "price": yes_px,
            "volume24hr": float(m.get("volume24hr") or 0) if m.get("volume24hr") not in (None, "") else 0.0,
            "closed": bool(m.get("closed")),
        })
    return out


def midpoint(token_id: str) -> float | None:
    try:
        j = _get(f"{CLOB}/midpoint", {"token_id": token_id})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    if isinstance(j, dict):
        v = j.get("mid") or j.get("price") or j.get("midpoint")
    else:
        v = j
    try:
        p = float(v)
    except (TypeError, ValueError):
        return None
    return p if 0.0 < p < 1.0 or p == 0 or p == 1 else p


def prices_history(token_id: str, fidelity: int = 1440) -> list[tuple[datetime, float]]:
    """Daily-ish mids. interval=max covers the series Polymarket stores."""
    try:
        j = _get(f"{CLOB}/prices-history", {
            "market": token_id,
            "interval": "max",
            "fidelity": int(fidelity),
        })
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return []
    hist = (j or {}).get("history") if isinstance(j, dict) else j
    rows = []
    for pt in hist or []:
        try:
            t = datetime.fromtimestamp(float(pt["t"]), tz=timezone.utc)
            p = float(pt["p"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append((t, p))
    return rows


def save_catalog(markets: list[dict], path: Path | None = None) -> Path:
    dest = path or CATALOG
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(markets, indent=2), encoding="utf-8")
    return dest


def load_catalog(path: Path | None = None) -> list[dict]:
    src = path or CATALOG
    if not src.exists():
        return []
    return json.loads(src.read_text(encoding="utf-8"))


def register_exchange(exchange: dict[str, str], catalog: list[dict] | None = None) -> dict[str, str]:
    """Mutate EXCHANGE map with POLY symbols from catalog."""
    for m in (catalog if catalog is not None else load_catalog()):
        sym = m.get("symbol")
        if sym:
            exchange[str(sym)] = "POLY"
    return exchange
