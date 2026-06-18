"""Measure per-preset stereo width on the stereo_field probe, through the real engine.

Reads the source probe and each preset's rendered probe under
competitors/<service>/, reports the L/R correlation change (negative = wider,
positive = narrower). Use to baseline width and to verify a width change worked
(re-render the probe into a new service slug, run again, compare).

  .venv/Scripts/python tools/measure_stereo_width.py [--service yesmaster-stereo-probe]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SIGNAL = "stereo_field_minus20.wav"
# per-preset M/S width baseline from dsp.rs (for reference in the printout)
WIDTH = {"oomph": 0.95, "warmth": 0.98, "tape": 0.99, "custom": 1.00, "clarity": 1.02,
         "loud": 1.03, "universal": 1.04, "punch": 1.04, "spatial": 1.16}


def corr(path):
    d, _ = sf.read(str(path), always_2d=True)
    if d.shape[1] < 2:
        return 1.0
    return float(np.corrcoef(d[:, 0], d[:, 1])[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="yesmaster-stereo-probe")
    args = ap.parse_args()
    src = ROOT / "source" / "test-signals" / SIGNAL
    base = corr(src)
    sdir = ROOT / "competitors" / args.service
    print(f"service={args.service}   input correlation={base:.3f}   "
          f"(negative Δ = wider, positive = narrower)\n")
    print(f"{'preset':10}{'width':>7}{'out corr':>10}{'corr Δ':>9}")
    rows = []
    for pre in sorted(WIDTH, key=WIDTH.get):
        p = sdir / pre / SIGNAL
        if not p.exists():
            print(f"{pre:10}{WIDTH[pre]:7.2f}    (missing)")
            continue
        c = corr(p)
        rows.append(c - base)
        print(f"{pre:10}{WIDTH[pre]:7.2f}{c:10.3f}{c - base:+9.3f}")
    if rows:
        print(f"\nspread (widest..narrowest): {max(rows) - min(rows):.3f} correlation units")


if __name__ == "__main__":
    main()
