#!/usr/bin/env python3
"""M4 – OpenAlgo-hosted Meridian V4 strategy.

Set MERIDIAN_ROOT to this repo. Upload/run this file in OpenAlgo Python Host.
MERIDIAN_MODE=dry  → no broker calls (default)
MERIDIAN_MODE=paper → OpenAlgo Strategy/api (Analyzer)

Env: OPENALGO_API_KEY, OPENALGO_HOST, OPENALGO_WEBHOOK_ID
Markets: India NSE + Delta crypto only.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(os.environ.get("MERIDIAN_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "decision"))
sys.path.insert(0, str(ROOT / "src" / "meta_label"))
sys.path.insert(0, str(ROOT / "src" / "openalgo"))

from broker import (  # noqa: E402
    atr_pct_from_history,
    ensure_analyzer,
    notify,
    refuse_live_if_analyzer,
)
from engine import (  # noqa: E402
    LIVE_BUDGET,
    PAPER_BUDGET,
    Intent,
    Position,
    RiskState,
    Signal,
    decide,
    manage,
)
from paper_sink import PAPER_CSV, append_close  # noqa: E402
from predict import load_artefact_safe  # noqa: E402
from primary import signal_from_quote  # noqa: E402
from quotes import DryFeed, FallbackFeed, OpenAlgoFeed, Quote, QuoteFeed, YFinanceFeed  # noqa: E402
from session import nse_open, to_ist  # noqa: E402
from state import dump as dump_state, killed, load as load_state  # noqa: E402

try:
    from model import load_model  # noqa: E402
except ImportError:  # pragma: no cover
    load_model = None  # type: ignore

_STOP = False


def request_stop(*_args) -> None:
    global _STOP
    _STOP = True
    print("shutdown requested", flush=True)

MODE = os.environ.get("MERIDIAN_MODE", "dry").lower()
HOST = os.environ.get("OPENALGO_HOST") or os.environ.get("HOST_SERVER", "http://127.0.0.1:5000")
WEBHOOK = os.environ.get("OPENALGO_WEBHOOK_ID", "")
API_KEY = os.environ.get("OPENALGO_API_KEY", "")
OA_USER = os.environ.get("OPENALGO_USERNAME", "")
STRATEGY_NAME = os.environ.get("STRATEGY_NAME", "MeridianV4")
LIVE_OK = os.environ.get("MERIDIAN_LIVE_OK", "0") == "1"
POLL_SEC = float(os.environ.get("MERIDIAN_POLL_SEC", "30"))
WATCH = [s.strip() for s in os.environ.get(
    "MERIDIAN_SYMBOLS", "INFY,HCLTECH,RELIANCE,TCS,BNBUSDT"
).split(",") if s.strip()]

# India cash + Delta only
EXCHANGE = {
    "INFY": "NSE", "HCLTECH": "NSE", "BHARTIARTL": "NSE", "M&M": "NSE",
    "BAJAJFINSV": "NSE", "GRASIM": "NSE", "NESTLEIND": "NSE", "BRITANNIA": "NSE",
    "RELIANCE": "NSE", "TCS": "NSE", "SBIN": "NSE",
    "BNBUSDT": "DELTA",
}
PRODUCT = {"NSE": "MIS", "DELTA": "CNC"}


def _order_client():
    if MODE == "dry":
        return None, None
    if API_KEY:
        from openalgo import api  # type: ignore
        return "api", api(api_key=API_KEY, host=HOST)
    if WEBHOOK:
        from openalgo import Strategy  # type: ignore
        return "wh", Strategy(host_url=HOST, webhook_id=WEBHOOK)
    raise RuntimeError("paper/live needs OPENALGO_API_KEY or OPENALGO_WEBHOOK_ID")


def _quote_feed() -> QuoteFeed:
    yf = YFinanceFeed()
    if MODE == "dry":
        return DryFeed()
    if not API_KEY:
        return yf  # paper-train without broker quotes
    from openalgo import api  # type: ignore
    return FallbackFeed(OpenAlgoFeed(api(api_key=API_KEY, host=HOST)), yf)


def _qty(price: float, size_pct: float, budget: float | None = None) -> float:
    budget = PAPER_BUDGET if budget is None else budget
    if MODE == "live":
        budget = LIVE_BUDGET
    risk = max(budget * size_pct, 0.0)
    if price <= 0:
        return 0.0
    q = risk / price
    return max(1.0, round(q, 1)) if price < 5000 else max(0.01, round(q, 4))


def preflight(client) -> None:
    if MODE == "live":
        if not LIVE_OK:
            raise RuntimeError("live refused: set MERIDIAN_LIVE_OK=1 after M5 gates pass")
        if killed():
            raise RuntimeError("live refused: research/runtime/KILL present")
        refuse_live_if_analyzer(client)
    elif MODE == "paper" and client is not None:
        ensure_analyzer(client, True)


class Host:
    def __init__(self, persist: bool = True, sink: Path | None = None, restore: bool = False):
        self.model = load_model() if load_model else None
        self.art = self.model.artefact if self.model is not None else load_artefact_safe()
        self.kind, self.client = _order_client()
        self.persist = persist
        self.sink = sink if sink is not None else (PAPER_CSV if MODE == "paper" else None)
        self.risk = RiskState(live=(MODE == "live"), killed=killed())
        self.pos: dict[str, Position] = {}
        self.heat = 0.0
        if restore:
            self.pos, self.risk = load_state()
            self.risk.live = MODE == "live"
            self.risk.killed = self.risk.killed or killed()
            self.heat = sum(p.size_pct for p in self.pos.values())
            self.risk.n_open = len(self.pos)
        if MODE in ("paper", "live"):
            preflight(self.client)
        kind = self.model.kind if self.model is not None else "json"
        ver = self.model.version if self.model is not None else "?"
        print(f"model {kind} v={ver} trained={getattr(self.model, 'trained', False)}", flush=True)

    def _save(self) -> None:
        if self.persist and MODE != "dry":
            dump_state(self.pos, self.risk)

    def _send(self, symbol: str, action: str, qty: float,
              last_price: float = 0.0, now: Optional[datetime] = None) -> bool:
        print(f"{MODE} {action} {symbol} qty={qty}", flush=True)
        notify(self.client, OA_USER, f"{STRATEGY_NAME} {MODE} {action} {symbol} x{qty}")
        if self.client is None:
            return True
        try:
            if self.kind == "api":
                ex = EXCHANGE.get(symbol, "NSE")
                product = PRODUCT.get(ex, "MIS")
                ptype = "MARKET"
                kw = {}
                # Paper after square-off / weekend: CNC LIMIT (Analyzer still records)
                if MODE == "paper" and ex == "NSE" and not nse_open(now or datetime.now(timezone.utc)):
                    product = "CNC"
                    ptype = "LIMIT"
                    if last_price > 0:
                        kw["price"] = str(round(last_price, 2))
                self.client.placeorder(
                    strategy=STRATEGY_NAME, symbol=symbol, action=action,
                    exchange=ex, price_type=ptype, product=product, quantity=qty, **kw,
                )
            else:
                self.client.strategyorder(symbol, action, qty)
            return True
        except Exception as e:
            print("order_fail", symbol, action, e, flush=True)
            return False

    def on_signal(self, sig: Signal, last_price: float, now: Optional[datetime] = None) -> Intent:
        now = now or datetime.now(timezone.utc)
        self.risk.roll_day(to_ist(now).date().isoformat())
        self.risk.killed = self.risk.killed or killed()
        self.risk.n_open = len(self.pos)
        sym = sig.symbol
        sig.portfolio_heat = self.heat

        if last_price <= 0:
            return Intent("FLAT", 0.0, 0.0, "bad_price")

        if sym in self.pos:
            intent = manage(self.pos[sym], last_price, now, sig.minutes_to_eod)
            if intent.action == "SELL":
                pos = self.pos[sym]
                qty = pos.qty or _qty(last_price, pos.size_pct)
                if not self._send(sym, "SELL", qty, last_price, now):
                    return Intent("HOLD", pos.size_pct, pos.stop_pct, "order_fail",
                                  meta_prob=pos.meta_prob)
                self.pos.pop(sym)
                self.heat = max(0.0, self.heat - pos.size_pct)
                hold = (now - pos.entry_ts).total_seconds()
                pnl = (last_price - pos.entry_price) * qty
                self.risk.daily_pnl += pnl
                self.risk.n_open = len(self.pos)
                if intent.reason in ("hard_stop", "trail"):
                    self.risk.arm_cooldown(sym, now)
                if self.persist:
                    append_close({
                        "symbol": sym,
                        "buy_price": pos.entry_price,
                        "sell_price": last_price,
                        "buy_time": pos.entry_ts.isoformat(),
                        "sell_time": now.isoformat(),
                        "hold_sec": hold,
                        "honest_pnl": pnl,
                        "qty": qty,
                        "risk_rupees": pos.entry_price * qty * pos.stop_pct,
                        "meta_prob": pos.meta_prob,
                        "atr_pct": pos.stop_pct / 1.5,
                        "approx_stop_pct": pos.stop_pct,
                        "confidence": sig.confidence,
                        "confluence": sig.confluence,
                        "p_success": sig.p_success,
                        "minutes_to_eod_flatten": sig.minutes_to_eod,
                        "minutes_since_midnight": sig.minutes_since_midnight,
                        "belief_posterior": sig.belief_posterior,
                        "portfolio_heat_at_entry": self.heat,
                        "model_version": f"v4_{MODE}",
                        "exit_reason": intent.reason,
                    }, self.sink)
                self._save()
            return intent

        intent = decide(sig, self.art, self.risk, now)
        if intent.action == "BUY":
            qty = _qty(last_price, intent.size_pct)
            if not self._send(sym, "BUY", qty, last_price, now):
                return Intent("FLAT", 0.0, 0.0, "order_fail", meta_prob=intent.meta_prob)
            self.pos[sym] = Position(
                symbol=sym, entry_price=last_price, entry_ts=now,
                stop_pct=intent.stop_pct, size_pct=intent.size_pct,
                meta_prob=intent.meta_prob, high_since_entry=last_price, qty=qty,
            )
            self.heat = min(1.0, self.heat + intent.size_pct)
            self.risk.n_open = len(self.pos)
            self._save()
        return intent


def pairs(symbols: list[str] | None = None) -> list[tuple[str, str]]:
    return [(s, EXCHANGE[s]) for s in (symbols or WATCH) if s in EXCHANGE]


def poll_once(
    host: Host,
    feed: QuoteFeed,
    symbols: list[str] | None = None,
    now: Optional[datetime] = None,
) -> list[Intent]:
    now = now or datetime.now(timezone.utc)
    try:
        got = feed.fetch(pairs(symbols))
    except Exception as e:
        print("quote_fail", e, flush=True)
        return []
    intents: list[Intent] = []
    for sym, q in (got or {}).items():
        try:
            if q.exchange == "NSE" and not nse_open(now) and MODE != "dry":
                continue
            sig = signal_from_quote(q, now)
            if MODE != "dry" and host.kind == "api":
                ap = atr_pct_from_history(host.client, q.symbol, q.exchange)
                if ap:
                    sig.atr_pct = ap
                    sig.approx_stop_pct = 1.5 * ap
            intents.append(host.on_signal(sig, q.ltp, now))
        except Exception as e:
            print("tick_fail", sym, e, flush=True)
    return intents


def run(max_ticks: Optional[int] = None, interval: Optional[float] = None,
        feed: Optional[QuoteFeed] = None) -> None:
    import signal as _signal
    import time as _t
    try:
        _signal.signal(_signal.SIGTERM, request_stop)
        _signal.signal(_signal.SIGINT, request_stop)
    except (ValueError, OSError):
        pass
    host = Host(persist=(MODE != "dry"), restore=(MODE != "dry"))
    feed = feed or _quote_feed()
    n, gap = 0, interval if interval is not None else POLL_SEC
    print(f"MeridianV4 run mode={MODE} watch={WATCH} poll={gap}s", flush=True)
    while not _STOP:
        intents = poll_once(host, feed)
        print(f"tick={n} open={list(host.pos)} n={len(intents)}", flush=True)
        n += 1
        if max_ticks is not None and n >= max_ticks:
            break
        slept = 0.0
        while slept < gap and not _STOP:
            step = min(0.5, gap - slept)
            _t.sleep(step)
            slept += step
    host._save()
    print("stopped", flush=True)


def dry_demo() -> list[str]:
    h = Host(persist=False)
    now = datetime(2026, 8, 15, 4, 30, tzinfo=timezone.utc)
    sig = Signal(0.62, 73.6, 0.676, 0.018, 90, 0.251208,
                 minutes_since_midnight=480, symbol="INFY")
    out = []
    i0 = h.on_signal(sig, 1500.0, now)
    out.append(i0.action)
    i1 = h.on_signal(sig, 1502.0, now.replace(minute=32))  # still min-hold
    out.append(i1.reason)
    i2 = h.on_signal(sig, 1570.0, now.replace(hour=5, minute=0))  # ~1.7R → TP
    out.append(i2.reason)
    return out


if __name__ == "__main__":
    print("MeridianV4", MODE, "watch", WATCH)
    if os.environ.get("MERIDIAN_LOOP", "0") == "1":
        n = int(os.environ.get("MERIDIAN_MAX_TICKS", "0") or 0)
        run(max_ticks=n or None)
    else:
        print("demo", dry_demo())
