"""Append paper/live closes to the V4 training set. Never touches V3."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels.csv"
PAPER_CSV = ROOT / "data" / "meta_labels" / "meridian_v4_paper_fills.csv"

SHORT_HOLD_SEC = 120
MIN_QUALITY_HOLD_SEC = 300

FIELDS = [
    "confidence", "confluence", "p_success", "atr", "atr_pct", "approx_stop_pct",
    "minutes_since_midnight", "minutes_to_eod_flatten", "belief_posterior",
    "qty", "risk_rupees", "is_futures", "is_contaminated_futures", "is_clean",
    "is_short_hold", "is_quality_hold", "hold_bucket", "exit_quality",
    "y_binary", "honest_pnl", "y_R", "hold_sec", "symbol", "signal_id",
    "buy_time", "sell_time", "buy_price", "sell_price", "fees", "atr_source",
    "model_version", "feature_hash", "regime_id", "meta_prob",
    "portfolio_heat_at_entry", "is_synthetic", "exit_reason",
]


def _fieldnames(dest: Path) -> list[str]:
    if dest.exists() and dest.stat().st_size > 0:
        with open(dest, encoding="utf-8", newline="") as f:
            row = next(csv.reader(f), None)
        if row:
            return row
    return FIELDS


def _bucket(hold: float) -> str:
    if hold < 60:
        return "<1m"
    if hold < 120:
        return "1-2m"
    if hold < 300:
        return "2-5m"
    if hold < 900:
        return "5-15m"
    return ">15m"


def close_to_row(fill: Mapping) -> dict:
    hold = float(fill.get("hold_sec") or 0.0)
    pnl = float(fill.get("honest_pnl") or 0.0)
    risk = float(fill.get("risk_rupees") or 0.0) or 1e-9
    conf = float(fill.get("confidence") or 0.0)
    confu = float(fill.get("confluence") or 0.0)
    p_suc = float(fill.get("p_success") or 0.0)
    atr_pct = float(fill.get("atr_pct") or 0.0)
    mins_eod = float(fill.get("minutes_to_eod_flatten") or 0.0)
    belief = float(fill.get("belief_posterior") or 0.0)
    feat = f"{conf:.6f}|{confu:.4f}|{p_suc:.6f}|{atr_pct:.6f}|{mins_eod:.2f}|{belief:.6f}"
    quality = hold >= MIN_QUALITY_HOLD_SEC
    short = hold < SHORT_HOLD_SEC
    return {
        "confidence": conf,
        "confluence": confu,
        "p_success": p_suc,
        "atr": fill.get("atr", atr_pct * float(fill.get("buy_price") or 0.0)),
        "atr_pct": atr_pct,
        "approx_stop_pct": fill.get("approx_stop_pct", 1.5 * atr_pct),
        "minutes_since_midnight": fill.get("minutes_since_midnight", 0),
        "minutes_to_eod_flatten": mins_eod,
        "belief_posterior": belief,
        "qty": fill.get("qty", 0),
        "risk_rupees": fill.get("risk_rupees", 0),
        "is_futures": int(fill.get("is_futures") or 0),
        "is_contaminated_futures": 0,
        "is_clean": 1,
        "is_short_hold": int(short),
        "is_quality_hold": int(quality),
        "hold_bucket": _bucket(hold),
        "exit_quality": "quality" if quality else ("scratch" if short else "medium"),
        "y_binary": int(pnl > 0),
        "honest_pnl": pnl,
        "y_R": pnl / risk,
        "hold_sec": hold,
        "symbol": fill.get("symbol", ""),
        "signal_id": fill.get("signal_id", 0),
        "buy_time": fill.get("buy_time", ""),
        "sell_time": fill.get("sell_time", ""),
        "buy_price": fill.get("buy_price", 0),
        "sell_price": fill.get("sell_price", 0),
        "fees": fill.get("fees", 0),
        "atr_source": fill.get("atr_source", "paper"),
        "model_version": fill.get("model_version", "v4_paper"),
        "feature_hash": hashlib.md5(feat.encode()).hexdigest()[:12],
        "regime_id": fill.get("regime_id", 0),
        "meta_prob": fill.get("meta_prob", ""),
        "portfolio_heat_at_entry": fill.get("portfolio_heat_at_entry", ""),
        "is_synthetic": 0,
        "exit_reason": fill.get("exit_reason", ""),
    }


def append_close(fill: Mapping, path: Path | None = None) -> Path:
    dest = Path(path) if path else DEFAULT_CSV
    dest.parent.mkdir(parents=True, exist_ok=True)
    row = close_to_row(fill)
    new = not dest.exists() or dest.stat().st_size == 0
    names = FIELDS if new else _fieldnames(dest)
    with open(dest, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)
    return dest
