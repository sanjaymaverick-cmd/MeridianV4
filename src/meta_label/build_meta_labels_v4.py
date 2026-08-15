#!/usr/bin/env python3
"""
Meridian V4 – Meta-label builder & cleaner
------------------------------------------
Works from existing V3 meta_label_training table / CSV.
Adds longer-hold redesign flags, clean equity mask,
contamination flags, and validation-ready schema.
Causal discipline preserved.
"""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timezone

ARTIFACTS = Path("/home/workdir/artifacts")
SRC_CSV = ARTIFACTS / "meridian_v3_meta_labels.csv"
SRC_DB = ARTIFACTS / "meridian_v3_with_meta_labels.db"
OUT_CSV = ARTIFACTS / "meridian_v4_meta_labels.csv"
OUT_DB = ARTIFACTS / "meridian_v4_meta_labels.db"
VAL_REPORT = ARTIFACTS / "M1_validation_report.md"

# Thresholds for longer-hold redesign (decision locked)
SHORT_HOLD_SEC = 120          # still flag as short
MIN_QUALITY_HOLD_SEC = 300    # target minimum for "quality" holds
FUTURES_SYMBOLS = {"NIFTY.F", "INFY.F", "BANKNIFTY.F", "NIFTY.C", "BANKNIFTY.C"}


def load_v3() -> pd.DataFrame:
    if SRC_CSV.exists():
        df = pd.read_csv(SRC_CSV, parse_dates=["buy_time", "sell_time"])
        print(f"Loaded {len(df)} rows from CSV")
        return df
    conn = sqlite3.connect(SRC_DB)
    df = pd.read_sql("SELECT * FROM meta_label_training", conn, parse_dates=["buy_time", "sell_time"])
    conn.close()
    print(f"Loaded {len(df)} rows from DB")
    return df


def add_v4_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Contamination & cleanliness ---
    df["is_futures"] = df["symbol"].isin(FUTURES_SYMBOLS).astype(int)
    df["is_contaminated_futures"] = (
        (df["is_futures"] == 1) & (df["honest_pnl"].abs() > 20)
    ).astype(int)  # large artificial PnL from mark mismatch

    # Clean equity/crypto mask (primary training set)
    df["is_clean"] = (
        (df["is_futures"] == 0) &
        (df["atr"].notna()) &
        (df["buy_price"] > 0) &
        (df["sell_price"] > 0)
    ).astype(int)

    # --- Longer-hold redesign flags ---
    df["is_short_hold"] = (df["hold_sec"] < SHORT_HOLD_SEC).astype(int)
    df["is_quality_hold"] = (df["hold_sec"] >= MIN_QUALITY_HOLD_SEC).astype(int)
    df["hold_bucket"] = pd.cut(
        df["hold_sec"],
        bins=[-np.inf, 60, 120, 300, 900, np.inf],
        labels=["<1m", "1-2m", "2-5m", "5-15m", ">15m"]
    ).astype(str)

    # Simple exit quality proxy (will be replaced by real exit_reason later)
    df["exit_quality"] = np.where(
        df["is_quality_hold"] == 1, "quality",
        np.where(df["is_short_hold"] == 1, "scratch", "medium")
    )

    # --- Placeholders for continuous / mlfinlab pipeline ---
    df["model_version"] = "v3_baseline"
    df["feature_hash"] = df.apply(
        lambda r: hashlib.md5(
            f"{r['confidence']:.6f}|{r['confluence']:.4f}|{r['p_success']:.6f}|"
            f"{r['atr_pct']:.6f}|{r['minutes_to_eod_flatten']:.2f}|{r['belief_posterior']:.6f}"
            .encode()
        ).hexdigest()[:12],
        axis=1
    )
    df["regime_id"] = 0          # will be filled by regime model later
    df["meta_prob"] = np.nan     # filled after model inference
    df["portfolio_heat_at_entry"] = np.nan

    # Keep original y_binary / y_R / honest_pnl untouched (honest accounting)
    return df


def validate(df: pd.DataFrame) -> dict:
    clean = df[df["is_clean"] == 1]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(df),
        "clean_rows": len(clean),
        "futures_rows": int(df["is_futures"].sum()),
        "contaminated_futures": int(df["is_contaminated_futures"].sum()),
        "short_holds": int(df["is_short_hold"].sum()),
        "quality_holds": int(df["is_quality_hold"].sum()),
        "clean_win_rate": float(clean["y_binary"].mean()) if len(clean) else None,
        "clean_avg_pnl": float(clean["honest_pnl"].mean()) if len(clean) else None,
        "clean_median_hold_sec": float(clean["hold_sec"].median()) if len(clean) else None,
        "atr_coverage": float(df["atr"].notna().mean()),
        "null_counts": df.isnull().sum().to_dict(),
        "hold_bucket_counts": df["hold_bucket"].value_counts().to_dict(),
        "symbol_counts_top10": df["symbol"].value_counts().head(10).to_dict(),
    }
    return report


def write_validation_report(report: dict, df: pd.DataFrame):
    clean = df[df["is_clean"] == 1]
    lines = [
        "# M1 Validation Report – Meridian V4 Meta Labels",
        f"**Generated:** {report['generated_at']}",
        "",
        "## Summary",
        f"- Total rows: **{report['total_rows']}**",
        f"- Clean rows (non-futures, valid price/ATR): **{report['clean_rows']}**",
        f"- Futures rows: {report['futures_rows']} (contaminated: {report['contaminated_futures']})",
        f"- Short holds (<{SHORT_HOLD_SEC}s): {report['short_holds']}",
        f"- Quality holds (≥{MIN_QUALITY_HOLD_SEC}s): {report['quality_holds']}",
        "",
        "## Clean Subset Metrics (primary training set)",
        f"- Win rate: **{report['clean_win_rate']:.1%}**" if report['clean_win_rate'] is not None else "- Win rate: n/a",
        f"- Avg honest PnL: ₹{report['clean_avg_pnl']:.2f}" if report['clean_avg_pnl'] is not None else "",
        f"- Median hold: {report['clean_median_hold_sec']:.1f}s" if report['clean_median_hold_sec'] is not None else "",
        f"- ATR coverage (full set): {report['atr_coverage']:.1%}",
        "",
        "## Hold Buckets",
        "```",
        json.dumps(report["hold_bucket_counts"], indent=2),
        "```",
        "",
        "## Top Symbols",
        "```",
        json.dumps(report["symbol_counts_top10"], indent=2),
        "```",
        "",
        "## Notes for M2 (mlfinlab)",
        "- Use `is_clean == 1` as the base filter before triple-barrier.",
        "- `is_quality_hold` is the target regime we want to increase.",
        "- Contaminated futures must stay excluded until mark pipeline is fixed.",
        "- `feature_hash` enables exact reproducibility of decision-time features.",
        "",
        "## Next",
        "Proceed to M2 – full mlfinlab-style meta-label pipeline on the clean subset.",
    ]
    VAL_REPORT.write_text("\n".join(lines))
    print(f"Validation report → {VAL_REPORT}")


def main():
    print("=== Meridian V4 Meta-Label Builder (M1) ===")
    df = load_v3()
    df = add_v4_columns(df)

    # Column order – stable for downstream
    core_features = [
        "confidence", "confluence", "p_success",
        "atr", "atr_pct", "approx_stop_pct",
        "minutes_since_midnight", "minutes_to_eod_flatten",
        "belief_posterior", "qty", "risk_rupees",
    ]
    flags = [
        "is_futures", "is_contaminated_futures", "is_clean",
        "is_short_hold", "is_quality_hold", "hold_bucket", "exit_quality",
    ]
    labels = ["y_binary", "honest_pnl", "y_R", "hold_sec"]
    meta = [
        "symbol", "signal_id", "buy_time", "sell_time",
        "buy_price", "sell_price", "fees", "atr_source",
        "model_version", "feature_hash", "regime_id",
        "meta_prob", "portfolio_heat_at_entry",
    ]
    ordered = [c for c in core_features + flags + labels + meta if c in df.columns]
    df = df[ordered].sort_values("buy_time").reset_index(drop=True)

    report = validate(df)
    write_validation_report(report, df)

    # Persist
    df.to_csv(OUT_CSV, index=False)
    print(f"CSV → {OUT_CSV} ({len(df)} rows)")

    conn = sqlite3.connect(OUT_DB)
    df.to_sql("meta_label_training", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mlt_time ON meta_label_training(buy_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mlt_clean ON meta_label_training(is_clean)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mlt_quality ON meta_label_training(is_quality_hold)")
    conn.commit()
    conn.close()
    print(f"DB  → {OUT_DB}")

    print("\n=== M1 DONE ===")
    print(f"Clean rows ready for mlfinlab: {report['clean_rows']}")
    print(f"Quality holds: {report['quality_holds']}  |  Short holds: {report['short_holds']}")


if __name__ == "__main__":
    main()
