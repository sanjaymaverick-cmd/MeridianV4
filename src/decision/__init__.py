"""Meridian decision engine (pure Python, OpenAlgo-ready)."""
try:
    from .engine import (  # noqa: F401
        DAILY_LOSS_LIMIT,
        LIVE_BUDGET,
        MAX_HEAT,
        MAX_SIZE,
        MAX_SIZE_LIVE,
        MIN_HOLD_SEC,
        MIN_META_PROB,
        PAPER_BUDGET,
        Engine,
        Intent,
        Position,
        RiskState,
        Signal,
        decide,
        manage,
        score,
    )
except ImportError:  # script path (OpenAlgo / pytest sys.path)
    from engine import (  # noqa: F401
        DAILY_LOSS_LIMIT,
        LIVE_BUDGET,
        MAX_HEAT,
        MAX_SIZE,
        MAX_SIZE_LIVE,
        MIN_HOLD_SEC,
        MIN_META_PROB,
        PAPER_BUDGET,
        Engine,
        Intent,
        Position,
        RiskState,
        Signal,
        decide,
        manage,
        score,
    )
