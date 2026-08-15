"""M5 promotion gates. Aggressive once cleared. Real rows only. Never synth."""
from __future__ import annotations

from dataclasses import asdict, dataclass

# Aggressive floors — still block scaffolding.
MIN_REAL_CLEAN = 80
MIN_REAL_QUALITY = 25
MIN_REAL_Y_META_POS = 15
MIN_PURGED_AUC = 0.55
MIN_CPCV_AUC = 0.55
MAX_AUC_GAP = 0.18
MIN_QUALITY_FRAC = 0.25


@dataclass
class Check:
    name: str
    ok: bool
    value: object
    need: object


@dataclass
class GateReport:
    passed: bool
    checks: list[Check]
    reason: str

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "checks": [asdict(c) for c in self.checks],
        }


def evaluate(m: dict) -> GateReport:
    """`m` must be computed on is_synthetic==0 (except n_synth_in_eval)."""
    n_real = int(m.get("n_real") or 0)
    n_qual = int(m.get("n_real_quality") or 0)
    n_pos = int(m.get("n_real_y_meta_pos") or 0)
    purged = m.get("purged_auc")
    cpcv = m.get("cpcv_auc")
    ins = m.get("in_sample_auc")
    gap = (float(ins) - float(purged)) if (ins is not None and purged is not None) else None
    qf = (n_qual / n_real) if n_real else 0.0
    synth_eval = int(m.get("n_synth_in_eval") or 0)

    checks = [
        Check("n_real_clean", n_real >= MIN_REAL_CLEAN, n_real, MIN_REAL_CLEAN),
        Check("n_real_quality", n_qual >= MIN_REAL_QUALITY, n_qual, MIN_REAL_QUALITY),
        Check("n_real_y_meta_pos", n_pos >= MIN_REAL_Y_META_POS, n_pos, MIN_REAL_Y_META_POS),
        Check("purged_auc", purged is not None and float(purged) >= MIN_PURGED_AUC, purged, MIN_PURGED_AUC),
        Check("cpcv_auc", cpcv is not None and float(cpcv) >= MIN_CPCV_AUC, cpcv, MIN_CPCV_AUC),
        Check("auc_gap", gap is not None and gap <= MAX_AUC_GAP, gap, MAX_AUC_GAP),
        Check("quality_frac", qf >= MIN_QUALITY_FRAC, round(qf, 4), MIN_QUALITY_FRAC),
        Check("eval_real_only", synth_eval == 0, synth_eval, 0),
    ]
    failed = [c.name for c in checks if not c.ok]
    passed = not failed
    reason = "ok" if passed else "fail:" + ",".join(failed)
    return GateReport(passed, checks, reason)


def latest_from_registry() -> GateReport | None:
    from pathlib import Path
    import json
    idx = Path(__file__).resolve().parents[2] / "research" / "registry" / "index.jsonl"
    if not idx.exists():
        return None
    last = None
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = json.loads(line)
    if not last:
        return None
    g = last.get("gates") or {}
    if "checks" in g:
        return evaluate(last.get("metrics") or {})
    return evaluate(last.get("metrics") or {})


if __name__ == "__main__":
    import json
    r = latest_from_registry()
    if r is None:
        print("no registry entries")
    else:
        print(json.dumps(r.as_dict(), indent=2))
        raise SystemExit(0 if r.passed else 1)
