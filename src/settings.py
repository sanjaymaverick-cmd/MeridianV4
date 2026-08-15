"""Env + locked defaults. No secrets. OpenAlgo injects OPENALGO_* at host time."""
from __future__ import annotations

import os

from paths import ROOT

APP_NAME = "MeridianV4"
VERSION = "0.4.0"


def _s(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return default if v is None or v == "" else v


def _f(name: str, default: float) -> float:
    try:
        return float(_s(name, str(default)))
    except ValueError:
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(float(_s(name, str(default))))
    except ValueError:
        return default


def _b(name: str, default: bool = False) -> bool:
    v = _s(name, "1" if default else "0").strip().lower()
    return v in ("1", "true", "yes", "on")


# --- runtime ---
MODE = _s("MERIDIAN_MODE", "dry").lower()          # dry | paper | live
LIVE_OK = _b("MERIDIAN_LIVE_OK", False)
LOOP = _b("MERIDIAN_LOOP", False)
POLL_SEC = _f("MERIDIAN_POLL_SEC", 30.0)
MAX_TICKS = _i("MERIDIAN_MAX_TICKS", 0)
SYMBOLS_RAW = _s("MERIDIAN_SYMBOLS", "INFY,HCLTECH,RELIANCE,TCS,BNBUSDT")
WATCH = [s.strip() for s in SYMBOLS_RAW.split(",") if s.strip()]

# OpenAlgo host injects OPENALGO_HOST, OPENALGO_API_KEY, STRATEGY_*
HOST = _s("OPENALGO_HOST") or _s("HOST_SERVER", "http://127.0.0.1:5000")
API_KEY = _s("OPENALGO_API_KEY")
WEBHOOK = _s("OPENALGO_WEBHOOK_ID")
OA_USER = _s("OPENALGO_USERNAME")
STRATEGY_NAME = _s("STRATEGY_NAME", APP_NAME)
STRATEGY_ID = _s("STRATEGY_ID", "")
OA_EXCHANGE = _s("OPENALGO_STRATEGY_EXCHANGE", "")

# --- risk (aggressive once gates pass) ---
MIN_META_PROB = _f("MERIDIAN_MIN_META_PROB", 0.55)
MAX_HEAT = _f("MERIDIAN_MAX_HEAT", 0.35)
MAX_MINUTES_TO_EOD = _f("MERIDIAN_MAX_MINUTES_TO_EOD", 30.0)
MIN_HOLD_SEC = _f("MERIDIAN_MIN_HOLD_SEC", 300.0)
MAX_SIZE = _f("MERIDIAN_MAX_SIZE", 0.25)
MAX_SIZE_LIVE = _f("MERIDIAN_MAX_SIZE_LIVE", 0.10)
TP_R = _f("MERIDIAN_TP_R", 1.5)
TRAIL_ARM_R = _f("MERIDIAN_TRAIL_ARM_R", 1.0)
TRAIL_GIVEBACK_R = _f("MERIDIAN_TRAIL_GIVEBACK_R", 0.4)
EOD_FLATTEN_MIN = _f("MERIDIAN_EOD_FLATTEN_MIN", 15.0)
STOP_ATR_MULT = _f("MERIDIAN_STOP_ATR_MULT", 1.5)
STOP_PCT_MIN = _f("MERIDIAN_STOP_PCT_MIN", 0.008)
STOP_PCT_MAX = _f("MERIDIAN_STOP_PCT_MAX", 0.04)
COOLDOWN_SEC = _f("MERIDIAN_COOLDOWN_SEC", 600.0)
DAILY_LOSS_LIMIT = _f("MERIDIAN_DAILY_LOSS_LIMIT", -5000.0)
MAX_POS_PAPER = _i("MERIDIAN_MAX_POS_PAPER", 3)
MAX_POS_LIVE = _i("MERIDIAN_MAX_POS_LIVE", 2)
LIVE_BUDGET = _f("MERIDIAN_LIVE_BUDGET", 25_000.0)
PAPER_BUDGET = _f("MERIDIAN_PAPER_BUDGET", 100_000.0)


def ensure_root_env() -> None:
    os.environ.setdefault("MERIDIAN_ROOT", str(ROOT))
