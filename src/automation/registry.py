"""Model registry. Live artefact replaced only via promote()."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
REG_DIR = ROOT / "research" / "registry"
INDEX = REG_DIR / "index.jsonl"
LIVE = ROOT / "research" / "artefacts" / "meta_label_v4.json"
CAND_DIR = ROOT / "research" / "artefacts" / "candidates"


def _write(entry: dict) -> None:
    REG_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def register(path: Path, status: str, metrics: dict, gates: dict) -> dict:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "status": status,  # candidate | promoted | rejected | force
        "path": str(path).replace("\\", "/"),
        "metrics": metrics,
        "gates": gates,
    }
    _write(entry)
    return entry


def promote(candidate: Path, live: Path | None = None) -> Path:
    dest = Path(live) if live else LIVE
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.copy2(dest, dest.with_suffix(".json.bak"))
    shutil.copy2(candidate, dest)
    sidecar = Path(candidate).with_suffix(".txt")
    if sidecar.exists():
        shutil.copy2(sidecar, dest.with_suffix(".txt"))
    return dest


def rollback(live: Path | None = None) -> Path:
    dest = Path(live) if live else LIVE
    bak = dest.with_suffix(".json.bak")
    if not bak.exists():
        raise FileNotFoundError(f"no backup at {bak}")
    shutil.copy2(bak, dest)
    _write({
        "ts": datetime.now(timezone.utc).isoformat(),
        "status": "rollback",
        "path": str(dest).replace("\\", "/"),
        "metrics": {},
        "gates": {"passed": False, "reason": "manual_rollback"},
    })
    return dest


def latest(status: Optional[str] = None) -> Optional[dict]:
    if not INDEX.exists():
        return None
    last = None
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if status is None or rec.get("status") == status:
            last = rec
    return last
