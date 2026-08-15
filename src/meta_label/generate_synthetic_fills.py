#!/usr/bin/env python3
"""
Generate synthetic paper fills for Meridian V4
- Longer quality holds
- Realistic feature distributions from real clean set
- Controllable win rate
- Clearly marked as synthetic
"""

import hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REAL = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels.csv"
OUT = ROOT / "data" / "meta_labels" / "meridian_v4_meta_labels_synth.csv"
N_SYNTH = 400
TARGET_WIN_RATE = 0.28          # realistic for longer-hold regime
QUALITY_HOLD_RATIO = 0.55       # majority quality holds

SYMBOLS = ["INFY", "HCLTECH", "BHARTIARTL", "M&M", "BAJAJFINSV", "GRASIM",
           "NESTLEIND", "BRITANNIA", "RELIANCE", "TCS", "BNBUSDT", "SBIN"]

rng = np.random.default_rng(42)

def sample_features(n):
    conf = rng.normal(0.56, 0.06, n).clip(0.48, 0.78)
    conf = conf
    confu = rng.choice([70.4, 73.6], n, p=[0.05, 0.95])
    p_suc = rng.normal(0.676, 0.002, n).clip(0.65, 0.69)
    atr_pct = rng.lognormal(np.log(0.022), 0.18, n).clip(0.015, 0.06)
    stop_pct = 1.5 * atr_pct
    mins_mid = rng.integers(480, 600, n)
    mins_eod = np.maximum(0, 580 - mins_mid + rng.normal(0, 15, n)).clip(0, 180)
    belief = np.full(n, 0.251208)
    return conf, confu, p_suc, atr_pct, stop_pct, mins_mid, mins_eod, belief

def main():
    real = pd.read_csv(REAL, parse_dates=["buy_time", "sell_time"])
    clean = real[real.is_clean == 1].copy()
    print(f"Real clean: {len(clean)}")

    n = N_SYNTH
    conf, confu, p_suc, atr_pct, stop_pct, mins_mid, mins_eod, belief = sample_features(n)

    # Hold times – force more quality
    is_quality = rng.random(n) < QUALITY_HOLD_RATIO
    hold_sec = np.where(
        is_quality,
        rng.integers(320, 2400, n),          # 5–40 min
        rng.integers(60, 280, n)             # short but not pure scratch
    ).astype(float)

    # Win/loss with modest edge on quality holds
    base_p = np.where(is_quality, TARGET_WIN_RATE + 0.06, TARGET_WIN_RATE - 0.08)
    win = rng.random(n) < base_p

    # PnL: winners positive, losers negative, scale with ATR risk
    risk = stop_pct * rng.uniform(80, 250, n)   # rough rupee risk
    pnl = np.where(win, risk * rng.uniform(0.4, 2.2, n),
                        -risk * rng.uniform(0.6, 1.3, n))

    # Times
    base = datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
    buy_times = [base.replace(tzinfo=None) + timedelta(minutes=int(i*3.1 + rng.integers(0, 5))) for i in range(n)]
    sell_times = [bt + timedelta(seconds=float(hs)) for bt, hs in zip(buy_times, hold_sec)]

    rows = []
    for i in range(n):
        sym = rng.choice(SYMBOLS)
        buy_p = rng.uniform(200, 3200) if sym != "BNBUSDT" else rng.uniform(500, 700)
        sell_p = buy_p * (1 + pnl[i] / (risk[i] / stop_pct[i] + 1e-9) * 0.01)  # rough
        feat_str = f"{conf[i]:.6f}|{confu[i]:.4f}|{p_suc[i]:.6f}|{atr_pct[i]:.6f}|{mins_eod[i]:.2f}|{belief[i]:.6f}"
        rows.append({
            "confidence": conf[i],
            "confluence": confu[i],
            "p_success": p_suc[i],
            "atr": atr_pct[i] * buy_p,
            "atr_pct": atr_pct[i],
            "approx_stop_pct": stop_pct[i],
            "minutes_since_midnight": mins_mid[i],
            "minutes_to_eod_flatten": mins_eod[i],
            "belief_posterior": belief[i],
            "qty": round(rng.uniform(1, 8), 1),
            "risk_rupees": risk[i],
            "is_futures": 0,
            "is_contaminated_futures": 0,
            "is_clean": 1,
            "is_short_hold": int(hold_sec[i] < 120),
            "is_quality_hold": int(is_quality[i]),
            "hold_bucket": "5-15m" if 300 <= hold_sec[i] < 900 else (">15m" if hold_sec[i] >= 900 else "2-5m"),
            "exit_quality": "quality" if is_quality[i] else "medium",
            "y_binary": int(win[i]),
            "honest_pnl": round(pnl[i], 2),
            "y_R": round(pnl[i] / (risk[i] + 1e-9), 3),
            "hold_sec": hold_sec[i],
            "symbol": sym,
            "signal_id": 90000 + i,
            "buy_time": buy_times[i],
            "sell_time": sell_times[i],
            "buy_price": round(buy_p, 2),
            "sell_price": round(sell_p, 2),
            "fees": round(rng.uniform(2, 12), 2),
            "atr_source": "synthetic",
            "model_version": "synth_v4",
            "feature_hash": hashlib.md5(feat_str.encode()).hexdigest()[:12],
            "regime_id": 0,
            "meta_prob": np.nan,
            "portfolio_heat_at_entry": round(rng.uniform(0.05, 0.25), 3),
            "is_synthetic": 1,
        })

    synth = pd.DataFrame(rows)

    # Combine: real clean + synth
    clean = clean.copy()
    clean["is_synthetic"] = 0
    clean["buy_time"] = pd.to_datetime(clean["buy_time"]).dt.tz_localize(None)
    clean["sell_time"] = pd.to_datetime(clean["sell_time"]).dt.tz_localize(None)
    combined = pd.concat([clean, synth], ignore_index=True).sort_values("buy_time").reset_index(drop=True)

    combined.to_csv(OUT, index=False)
    print(f"Wrote {len(combined)} rows → {OUT}")
    print(f"  Real clean : {len(clean)}")
    print(f"  Synthetic  : {len(synth)}")
    print(f"  Synth win rate: {synth.y_binary.mean():.1%}")
    print(f"  Synth quality holds: {synth.is_quality_hold.sum()}")
    print(f"  Combined win rate: {combined.y_binary.mean():.1%}")

if __name__ == "__main__":
    main()
