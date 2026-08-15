#!/usr/bin/env python3
"""Training entry (scaffold).

Live scoring uses the JSON artefact today. This module is the seam for
the full mlfinlab-style trainer (LightGBM + sequential bootstrap).

TODO(training): do not implement until real paper quality holds exist.
  - sequential bootstrap sample weights (uniqueness.py already has the draw)
  - LightGBM binary on y_meta, purged/CPCV for selection
  - export booster + feature names next to JSON logistic
  - promote only via automation.retrain + gates (real rows only)
"""
from __future__ import annotations

from pathlib import Path


def train_lightgbm(labeled_csv: Path, dest: Path) -> dict:
    """TODO(training): fit LightGBM on real+optional-synth; eval real-only."""
    raise NotImplementedError(
        "TODO(training): LightGBM trainer waits for real quality holds. "
        "Use src/meta_label/m2_research_baseline.py (logistic JSON) until then."
    )


if __name__ == "__main__":
    raise SystemExit(
        "TODO(training): python src/meta_label/m2_research_baseline.py "
        "is the current trainer. LightGBM is gated on M5 real metrics."
    )
