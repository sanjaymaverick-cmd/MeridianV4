#!/usr/bin/env python3
"""M2 – mlfinlab-style meta-label baseline.

TBM + uniqueness weights + purged / combinatorial purged CV.
Trains portable logistic artefact for the decision engine.
Prefers combined set (real clean + synth). Real-only is logged separately.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from purged_cv import combinatorial_purged_kfold, purged_kfold  # noqa: E402
from triple_barrier import PT_MULT, SL_MULT, VERTICAL_SEC, label_trades  # noqa: E402
from uniqueness import average_uniqueness  # noqa: E402

ROOT = _HERE.parents[1]
REAL = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels.csv"
SYNTH = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels_synth.csv"
LABELED = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels_tbm.csv"
ARTEFACT_DIR = ROOT / "research" / "artefacts"
ARTEFACT = ARTEFACT_DIR / "meta_label_v4.json"
LEDGER = ROOT / "research" / "experiment_ledger.jsonl"

FEATURES = [
    "confidence",
    "confluence",
    "p_success",
    "atr_pct",
    "approx_stop_pct",
    "minutes_since_midnight",
    "minutes_to_eod_flatten",
]


def load_set() -> pd.DataFrame:
    src = SYNTH if SYNTH.exists() else REAL
    df = pd.read_csv(src, parse_dates=["buy_time", "sell_time"])
    df = df[df["is_clean"] == 1].copy()
    if "is_synthetic" not in df.columns:
        df["is_synthetic"] = 0
    df = df.sort_values("buy_time").reset_index(drop=True)
    print(f"source={src.name} n={len(df)} synth={int(df.is_synthetic.sum())} "
          f"y_bin_wr={df.y_binary.mean():.1%}")
    return df


def _safe_auc(y, p) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, p))


def eval_splits(X, y, w, splits) -> list[dict]:
    rows = []
    for i, (tr, te) in enumerate(splits):
        if y[tr].sum() == 0 or y[te].sum() == 0 or y[tr].sum() == len(tr):
            rows.append({"fold": i, "n_train": int(len(tr)), "n_test": int(len(te)),
                         "note": "skipped_degenerate"})
            continue
        sc = StandardScaler()
        Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
        clf = LogisticRegression(max_iter=800, class_weight="balanced", random_state=42)
        clf.fit(Xtr, y[tr], sample_weight=w[tr])
        proba = clf.predict_proba(Xte)[:, 1]
        pred = (proba >= 0.5).astype(int)
        rows.append({
            "fold": i,
            "n_train": int(len(tr)),
            "n_test": int(len(te)),
            "pos_test": int(y[te].sum()),
            "auc": _safe_auc(y[te], proba),
            "acc": float(accuracy_score(y[te], pred)),
            "logloss": float(log_loss(y[te], proba, labels=[0, 1])),
        })
    return rows


def fit_export(X, y, w) -> dict:
    sc = StandardScaler()
    Xs = sc.fit_transform(X)
    clf = LogisticRegression(max_iter=800, class_weight="balanced", random_state=42)
    clf.fit(Xs, y, sample_weight=w)
    proba = clf.predict_proba(Xs)[:, 1]
    art = {
        "model": "LogisticRegression",
        "version": "m2_tbm_v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "scaler_mean": sc.mean_.astype(float).tolist(),
        "scaler_scale": [max(float(s), 1e-8) for s in sc.scale_],
        "coef": clf.coef_.ravel().astype(float).tolist(),
        "intercept": float(clf.intercept_[0]),
        "threshold": 0.55,
        "tbm": {"pt_mult": PT_MULT, "sl_mult": SL_MULT, "vertical_sec": VERTICAL_SEC},
        "in_sample": {
            "n": int(len(y)),
            "pos": int(y.sum()),
            "auc": _safe_auc(y, proba),
            "acc": float(accuracy_score(y, (proba >= 0.5).astype(int))),
        },
        "note": "Scaffolding. Do not promote on synth-only metrics.",
    }
    ARTEFACT_DIR.mkdir(parents=True, exist_ok=True)
    ARTEFACT.write_text(json.dumps(art, indent=2), encoding="utf-8")
    return art


def log_experiment(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> None:
    print("=== M2 TBM + purged CV ===")
    df = load_set()
    df = label_trades(df)
    u = average_uniqueness(df["buy_time"], df["sell_time"])
    df["avg_uniqueness"] = u
    df.to_csv(LABELED, index=False)

    y = df["y_meta"].to_numpy()
    X = df[FEATURES].fillna(0).to_numpy(dtype=float)
    w = np.clip(u, 1e-6, None)

    print(f"TBM  +1={int((df.tbm_label==1).sum())}  -1={int((df.tbm_label==-1).sum())}  "
          f"0={int((df.tbm_label==0).sum())}  y_meta_wr={y.mean():.1%}")
    print(f"uniqueness mean={u.mean():.3f}  min={u.min():.3f}")

    pkf = list(purged_kfold(df["buy_time"], df["sell_time"], n_splits=4,
                            embargo=pd.Timedelta("5min")))
    cpcv = list(combinatorial_purged_kfold(df["buy_time"], df["sell_time"],
                                           n_groups=6, n_test_groups=2,
                                           embargo=pd.Timedelta("5min")))
    pkf_scores = eval_splits(X, y, w, pkf)
    cpcv_scores = eval_splits(X, y, w, cpcv)

    def _mean_auc(rows):
        vals = [r["auc"] for r in rows if r.get("auc") is not None]
        return float(np.mean(vals)) if vals else None

    art = fit_export(X, y, w)

    real = df[df.is_synthetic == 0]
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "milestone": "M2_tbm",
        "model": "LogisticRegression_balanced_uniqueness",
        "features": FEATURES,
        "n": int(len(df)),
        "n_real": int(len(real)),
        "n_synth": int(df.is_synthetic.sum()),
        "y_meta_pos": int(y.sum()),
        "y_meta_wr": float(y.mean()),
        "tbm": {"pt": PT_MULT, "sl": SL_MULT, "vertical_sec": VERTICAL_SEC,
                "pos": int((df.tbm_label == 1).sum()),
                "neg": int((df.tbm_label == -1).sum()),
                "vert": int((df.tbm_label == 0).sum())},
        "purged_kfold": pkf_scores,
        "purged_kfold_mean_auc": _mean_auc(pkf_scores),
        "cpcv_n_splits": len(cpcv_scores),
        "cpcv_mean_auc": _mean_auc(cpcv_scores),
        "in_sample_auc": art["in_sample"]["auc"],
        "artefact": str(ARTEFACT.relative_to(ROOT)).replace("\\", "/"),
        "labeled": str(LABELED.relative_to(ROOT)).replace("\\", "/"),
        "note": "TBM via ATR-scaled Brownian bridge. Synth scaffolding. No live promotion.",
    }
    log_experiment(entry)
    print(json.dumps({k: entry[k] for k in
                      ("n", "y_meta_wr", "purged_kfold_mean_auc",
                       "cpcv_mean_auc", "in_sample_auc", "artefact")}, indent=2))
    print("ledger →", LEDGER)
    print("M2 TBM DONE")


if __name__ == "__main__":
    main()
