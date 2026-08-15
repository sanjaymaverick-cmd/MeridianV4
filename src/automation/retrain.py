#!/usr/bin/env python3
"""M5 retrain job.

Trains a candidate artefact (TBM + purged CV). Evaluates gates on REAL rows
only. Promotes to live artefact only if gates pass (or --force, logged).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "meta_label"))
sys.path.insert(0, str(ROOT / "src" / "automation"))

from gates import evaluate  # noqa: E402
from m2_research_baseline import (  # noqa: E402
    FEATURES,
    REAL,
    SYNTH,
    combinatorial_purged_kfold,
    eval_splits,
    fit_export,
    label_trades,
    log_experiment,
    purged_kfold,
)
from registry import CAND_DIR, LIVE, promote, register  # noqa: E402
from uniqueness import average_uniqueness  # noqa: E402


def _mean_auc(rows) -> float | None:
    vals = [r["auc"] for r in rows if r.get("auc") is not None]
    return float(np.mean(vals)) if vals else None


def load_frames(include_synth: bool) -> pd.DataFrame:
    if include_synth and SYNTH.exists():
        df = pd.read_csv(SYNTH, parse_dates=["buy_time", "sell_time"])
    else:
        df = pd.read_csv(REAL, parse_dates=["buy_time", "sell_time"])
        if "is_synthetic" not in df.columns:
            df["is_synthetic"] = 0
    df = df[df["is_clean"] == 1].copy().sort_values("buy_time").reset_index(drop=True)
    return df


def real_metrics(df: pd.DataFrame, ins_auc: float | None) -> dict:
    real = df[df["is_synthetic"] == 0].copy()
    n_real = len(real)
    purged_auc = cpcv_auc = None
    if n_real >= 20 and int(real["y_meta"].sum()) >= 2:
        X = real[FEATURES].fillna(0).to_numpy(dtype=float)
        y = real["y_meta"].to_numpy()
        w = np.clip(real["avg_uniqueness"].to_numpy(), 1e-6, None)
        try:
            pkf = list(purged_kfold(real["buy_time"], real["sell_time"], n_splits=3))
            purged_auc = _mean_auc(eval_splits(X, y, w, pkf))
        except ValueError:
            purged_auc = None
        try:
            cpcv = list(combinatorial_purged_kfold(
                real["buy_time"], real["sell_time"], n_groups=5, n_test_groups=2))
            cpcv_auc = _mean_auc(eval_splits(X, y, w, cpcv))
        except ValueError:
            cpcv_auc = None
    return {
        "n_real": n_real,
        "n_real_quality": int(real["is_quality_hold"].sum()) if n_real else 0,
        "n_real_y_meta_pos": int(real["y_meta"].sum()) if n_real else 0,
        "purged_auc": purged_auc,
        "cpcv_auc": cpcv_auc,
        "in_sample_auc": ins_auc,
        "n_synth_in_eval": 0,
        "quality_frac_real": (
            float(real["is_quality_hold"].mean()) if n_real else 0.0
        ),
    }


def run(include_synth: bool = True, do_promote: bool = False, force: bool = False) -> dict:
    print("=== M5 retrain ===")
    df = load_frames(include_synth)
    df = label_trades(df)
    df["avg_uniqueness"] = average_uniqueness(df["buy_time"], df["sell_time"])
    y = df["y_meta"].to_numpy()
    X = df[FEATURES].fillna(0).to_numpy(dtype=float)
    w = np.clip(df["avg_uniqueness"].to_numpy(), 1e-6, None)

    vid = "m5_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = CAND_DIR / f"{vid}.json"
    art = fit_export(X, y, w, dest=dest, version=vid)

    metrics = real_metrics(df, art["in_sample"]["auc"])
    metrics["n_train"] = int(len(df))
    metrics["n_synth_train"] = int(df["is_synthetic"].sum())
    report = evaluate(metrics)

    status = "candidate"
    promoted = False
    if do_promote and report.passed:
        promote(dest, LIVE)
        status = "promoted"
        promoted = True
    elif do_promote and force:
        promote(dest, LIVE)
        status = "force"
        promoted = True
        print("FORCE promote — not gate-clean")
    elif do_promote and not report.passed:
        status = "rejected"
        print("promote blocked:", report.reason)

    rec = register(dest, status, metrics, report.as_dict())
    log_experiment({
        "ts": rec["ts"],
        "milestone": "M5",
        "version": vid,
        "status": status,
        "metrics": metrics,
        "gates": report.as_dict(),
        "artefact": str(dest).replace("\\", "/"),
        "promoted": promoted,
        "note": "Gates evaluate real rows only. Synth never promotion-eligible.",
    })
    print(json.dumps({
        "version": vid, "status": status, "passed": report.passed,
        "reason": report.reason, "metrics": metrics,
    }, indent=2))
    return {"version": vid, "status": status, "report": report, "metrics": metrics, "path": dest}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-synth", action="store_true", help="train on real CSV only")
    ap.add_argument("--promote", action="store_true", help="promote if gates pass")
    ap.add_argument("--force", action="store_true", help="promote even if gates fail (logged)")
    args = ap.parse_args()
    run(include_synth=not args.no_synth, do_promote=args.promote, force=args.force)


if __name__ == "__main__":
    main()
