"""Persist Host book across process restarts. No secrets."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine import Position, RiskState

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "research" / "runtime"
STATE = RUNTIME / "state.json"
KILL = RUNTIME / "KILL"


def killed() -> bool:
    return KILL.exists()


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def dump(pos: dict[str, Position], risk: RiskState, path: Path | None = None) -> Path:
    dest = Path(path) if path else STATE
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "positions": {
            s: {
                "symbol": p.symbol, "entry_price": p.entry_price,
                "entry_ts": _iso(p.entry_ts), "stop_pct": p.stop_pct,
                "size_pct": p.size_pct, "meta_prob": p.meta_prob,
                "high_since_entry": p.high_since_entry, "qty": p.qty,
            }
            for s, p in pos.items()
        },
        "risk": {
            "daily_pnl": risk.daily_pnl,
            "killed": risk.killed,
            "live": risk.live,
            "pnl_date": risk.pnl_date,
            "cooldown_until": {k: _iso(v) for k, v in risk.cooldown_until.items()},
        },
    }
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def load(path: Path | None = None) -> tuple[dict[str, Position], RiskState]:
    src = Path(path) if path else STATE
    risk = RiskState(killed=killed())
    if not src.exists():
        return {}, risk
    raw = json.loads(src.read_text(encoding="utf-8"))
    pos = {}
    for s, r in (raw.get("positions") or {}).items():
        pos[s] = Position(
            symbol=r["symbol"], entry_price=float(r["entry_price"]),
            entry_ts=datetime.fromisoformat(r["entry_ts"]),
            stop_pct=float(r["stop_pct"]), size_pct=float(r["size_pct"]),
            meta_prob=float(r["meta_prob"]), high_since_entry=float(r["high_since_entry"]),
            qty=float(r.get("qty") or 0.0),
        )
    rr = raw.get("risk") or {}
    risk.daily_pnl = float(rr.get("daily_pnl") or 0.0)
    risk.live = bool(rr.get("live") or False)
    risk.killed = risk.killed or bool(rr.get("killed") or False)
    risk.pnl_date = str(rr.get("pnl_date") or "")
    for k, v in (rr.get("cooldown_until") or {}).items():
        risk.cooldown_until[k] = datetime.fromisoformat(v)
    risk.n_open = len(pos)
    return pos, risk
