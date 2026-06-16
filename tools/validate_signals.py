"""
Step 1 of the method: validate the 8 source test signals against their
ground-truth spec. This also exercises the whole measurement stack before any
service data arrives.

Run:  .venv/Scripts/python tools/validate_signals.py

Writes:
  measurements/validation/<signal>.json   per-signal measurement + checks
  measurements/validation/summary.json    aggregate status + methodology
Prints a concise PASS/WARN/FAIL table.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import scipy
import soundfile as sf

import audio_metrics as am
import signals as sigreg

SRC = ROOT / "source" / "test-signals"
OUT = ROOT / "measurements" / "validation"

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
RANK = {PASS: 0, WARN: 1, FAIL: 2}


# --------------------------------------------------------------------------- #
# Check primitives — each returns a structured, JSON-able verdict.
# --------------------------------------------------------------------------- #
def _v(name, measured, expected, status, tol=None, note=""):
    return {"check": name, "measured": measured, "expected": expected,
            "tolerance": tol, "status": status, "note": note}


def check_equal(name, measured, expected, note=""):
    return _v(name, measured, expected, PASS if measured == expected else FAIL, note=note)


def check_approx(name, measured, expected, tol, unit="", warn_mult=2.0):
    if measured is None:
        return _v(name, measured, expected, FAIL, tol, "missing")
    d = abs(measured - expected)
    status = PASS if d <= tol else (WARN if d <= tol * warn_mult else FAIL)
    return _v(name, measured, expected, status, tol,
              f"|Δ|={d:.3f}{unit}")


def check_min(name, measured, threshold, note=""):
    if measured is None:
        return _v(name, measured, f">= {threshold}", FAIL, note="missing")
    return _v(name, measured, f">= {threshold}", PASS if measured >= threshold else FAIL, note=note)


def check_max(name, measured, threshold, note=""):
    if measured is None:
        return _v(name, measured, f"<= {threshold}", FAIL, note="missing")
    return _v(name, measured, f"<= {threshold}", PASS if measured <= threshold else FAIL, note=note)


# --------------------------------------------------------------------------- #
# Per-role check builders
# --------------------------------------------------------------------------- #
def common_checks(rec, exp):
    f = rec["format"]
    return [
        check_equal("sample_rate", f["sample_rate"], exp["sample_rate"]),
        check_equal("channels", f["channels"], exp["channels"]),
        check_equal("bit_depth", f["bit_depth"], exp["bit_depth"]),
        check_equal("frames", f["frames"], exp["frames"]),
        check_approx("duration_sec", f["duration_sec"], exp["duration_sec"], 0.001, "s"),
        check_approx("rms_dbfs", rec["levels"]["rms_dbfs"], exp["rms_dbfs"], exp["rms_tol"], "dB"),
    ]


def role_checks(role, rec, exp):
    out = []
    if role == "pink_noise":
        out.append(check_approx("spectral_slope_db_per_oct",
                                rec["spectral"]["slope_db_per_oct"],
                                exp["slope_db_per_oct"], exp["slope_tol"], "dB/oct"))
        if exp.get("stereo_decorrelated"):
            out.append(check_max("L-R correlation (decorrelated)",
                                 round(rec["stereo"]["correlation"], 3), 0.5,
                                 "independent stereo -> low correlation"))
    elif role == "sweep":
        ss = rec["signal_specific"]
        out.append(check_max("sweep start_hz near 20",
                             ss.get("dominant_start_hz"), 60))
        out.append(check_min("sweep end_hz near 20k",
                             ss.get("dominant_end_hz"), 15000))
        out.append(check_min("sweep monotonic_fraction",
                             ss.get("monotonic_fraction"), 0.90))
    elif role == "click_track":
        ss = rec["signal_specific"]
        out.append(check_equal("n_impulses", ss["n_impulses"], exp["n_impulses"]))
        out.append(check_approx("impulse_period_ms", ss["mean_period_ms"],
                                exp["impulse_period_ms"], exp["period_tol_ms"], "ms"))
    elif role == "tone_ladder":
        ss = rec["signal_specific"]
        bad = []
        for t in ss["tones"]:
            if t["expected_hz"]:
                tol = t["expected_hz"] * exp["freq_tol_pct"] / 100.0
                if abs(t["measured_hz"] - t["expected_hz"]) > tol:
                    bad.append(t)
        out.append(_v("all tone freqs within tol",
                      f"{len(ss['tones']) - len(bad)}/{len(ss['tones'])} ok",
                      f"+/- {exp['freq_tol_pct']}%", PASS if not bad else FAIL,
                      note=("" if not bad else f"off: {[(b['expected_hz'], b['measured_hz']) for b in bad]}")))
        out.append(check_max("tone level spread", ss["level_spread_db"],
                             exp["level_spread_tol_db"], "equal-amplitude tones"))
    elif role == "dynamic":
        ss = rec["signal_specific"]
        out.append(check_approx("loud segment level", ss["loud_mean_dbfs"],
                                exp["loud_dbfs"], exp["loud_tol"], "dB"))
        out.append(check_approx("quiet segment level", ss["quiet_mean_dbfs"],
                                exp["quiet_dbfs"], exp["quiet_tol"], "dB"))
        out.append(check_min("loud-quiet contrast", ss["contrast_db"],
                             exp["contrast_min_db"]))
    elif role == "mid_side":
        ss = rec["signal_specific"]
        out.append(check_min("L-R correlation", round(ss["correlation"], 3),
                             exp["correlation_min"]))
        out.append(check_approx("side-minus-mid", ss["side_minus_mid_db"],
                                exp["side_minus_mid_db"], exp["side_mid_tol"], "dB"))
    return out


def validate_one(filename, spec):
    role = spec["role"]
    exp = spec["expected"]
    rec = am.measure_file(SRC / filename, role=role)
    checks = common_checks(rec, exp) + role_checks(role, rec, exp)
    status = PASS
    for c in checks:
        status = max(status, c["status"], key=lambda s: RANK[s])
    return {
        "file": filename,
        "role": role,
        "purpose": spec["purpose"],
        "priority": spec["priority"],
        "status": status,
        "checks": checks,
        "measurement": rec,
    }


METHODOLOGY = {
    "loudness": "EBU R128 / ITU-R BS.1770 integrated LUFS and LRA via pyloudnorm.",
    "true_peak": "ITU-R BS.1770-style true peak via 4x polyphase oversampling (scipy.resample_poly).",
    "spectral": "Welch PSD (Hann, nperseg=16384, 50% overlap); band energy = sum(PSD*df) per band.",
    "slope": "Least-squares fit of PSD(dB) vs log-frequency over 50 Hz-16 kHz, reported per octave.",
    "tone_detect": "Per-segment FFT peak with parabolic interpolation; level = segment RMS (guard-banded).",
    "dbfs_convention": "20*log10(x), full scale = 1.0 (full-scale sine RMS = -3.01 dBFS).",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    missing = [fn for fn in sigreg.SIGNALS if not (SRC / fn).exists()]
    if missing:
        print(f"!! MISSING source signals: {missing}")

    for fn, spec in sorted(sigreg.SIGNALS.items(), key=lambda kv: kv[1]["priority"]):
        if not (SRC / fn).exists():
            continue
        res = validate_one(fn, spec)
        results.append(res)
        (OUT / f"{Path(fn).stem}.json").write_text(
            json.dumps(res, indent=2), encoding="utf-8", newline="\n")

    summary = {
        "report": "test-signal validation",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_signals": len(results),
        "all_present": not missing,
        "missing": missing,
        "overall_status": (FAIL if any(r["status"] == FAIL for r in results)
                           else WARN if any(r["status"] == WARN for r in results)
                           else PASS),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "soundfile": sf.__version__,
            "libsndfile": sf.__libsndfile_version__,
        },
        "methodology": METHODOLOGY,
        "signals": [{"file": r["file"], "role": r["role"], "status": r["status"],
                     "n_checks": len(r["checks"]),
                     "n_fail": sum(c["status"] == FAIL for c in r["checks"]),
                     "n_warn": sum(c["status"] == WARN for c in r["checks"])}
                    for r in results],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")

    # ---- console table ----
    print("\n" + "=" * 74)
    print(f"  TEST-SIGNAL VALIDATION  —  overall: {summary['overall_status']}")
    print("=" * 74)
    glyph = {PASS: "[PASS]", WARN: "[WARN]", FAIL: "[FAIL]"}
    for r in results:
        nf = sum(c["status"] == FAIL for c in r["checks"])
        nw = sum(c["status"] == WARN for c in r["checks"])
        print(f"  {glyph[r['status']]}  {r['file']:<28} "
              f"{len(r['checks'])} checks  ({nf} fail, {nw} warn)")
        for c in r["checks"]:
            if c["status"] != PASS:
                print(f"          {c['status']}: {c['check']} "
                      f"-> measured={c['measured']} expected={c['expected']} {c['note']}")
    print("=" * 74)
    print(f"  Wrote {len(results)} per-signal JSONs + summary.json to {OUT.relative_to(ROOT)}")
    print("=" * 74 + "\n")
    return 0 if summary["overall_status"] != FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
