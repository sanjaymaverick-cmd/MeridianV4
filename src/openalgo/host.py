#!/usr/bin/env python3
"""OpenAlgo /python upload entry.

Upload this file on http://127.0.0.1:5000/python
Set MERIDIAN_ROOT in OpenAlgo .env to this repo (absolute path).

Injected by OpenAlgo: OPENALGO_API_KEY, OPENALGO_HOST, STRATEGY_ID,
STRATEGY_NAME, OPENALGO_STRATEGY_EXCHANGE.

Default hosted mode is paper. Live requires MERIDIAN_LIVE_OK=1 after M5.
Analyzer ON for paper. stdout is the log.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _root() -> Path:
    env = os.environ.get("MERIDIAN_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "src" / "decision" / "engine.py").exists():
            return p
        raise SystemExit(f"MERIDIAN_ROOT={p} is not a MeridianV4 repo")
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "decision" / "engine.py").exists():
            return parent
    raise SystemExit("set MERIDIAN_ROOT to the MeridianV4 checkout")


ROOT = _root()
os.environ["MERIDIAN_ROOT"] = str(ROOT)
os.environ.setdefault("MERIDIAN_LOOP", "1")
os.environ.setdefault("MERIDIAN_MODE", "paper")

for p in (
    ROOT / "src",
    ROOT / "src" / "openalgo",
    ROOT / "src" / "decision",
    ROOT / "src" / "meta_label",
):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from strategy_v4 import run  # noqa: E402


def main() -> None:
    print("MeridianV4 host", ROOT, "mode", os.environ.get("MERIDIAN_MODE"), flush=True)
    n = int(os.environ.get("MERIDIAN_MAX_TICKS", "0") or 0)
    run(max_ticks=n or None)


if __name__ == "__main__":
    main()
