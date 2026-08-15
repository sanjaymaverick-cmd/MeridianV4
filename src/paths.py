"""Repo root. MERIDIAN_ROOT wins; else walk up from this file."""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()


def repo_root() -> Path:
    env = os.environ.get("MERIDIAN_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _HERE.parents[1]


ROOT = repo_root()
DATA = ROOT / "data" / "meta_labels"
ARTEFACTS = ROOT / "research" / "artefacts"
REGISTRY = ROOT / "research" / "registry"
RUNTIME = ROOT / "research" / "runtime"
LIVE_ARTEFACT = ARTEFACTS / "meta_label_v4.json"
