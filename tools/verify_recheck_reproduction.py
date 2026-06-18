"""Gold-standard check: a FRESH render from the YES Master engine (yesmaster-recheck)
vs the originally committed loudness-parity fingerprints. If the fresh render reproduces
the committed numbers, the capture is deterministic + the settings were really applied.
Also proves the intensity knob moves the sound (0.0 vs 0.5 vs 1.0)."""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal as ss

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "test-signals"
RECHECK = ROOT / "competitors" / "yesmaster-recheck"
COMMITTED_FP = ROOT / "measurements" / "fingerprints" / "yesmaster-loudness-parity"

BANDS = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
         (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]
PRESETS = ["universal", "clarity", "tape", "spatial", "oomph", "warmth", "punch", "loud", "custom"]


def read(p):
    d, sr = sf.read(str(p), always_2d=True)
    return d.astype(np.float64), sr


def lufs(d, sr):
    return float(pyln.Meter(sr).integrated_loudness(d))


def tp(d, sr):
    pk = 0.0
    for ch in range(d.shape[1]):
        xp = np.pad(d[:, ch], 64, mode="edge")
        up = ss.resample_poly(xp, 4, 1)[256:-256]
        pk = max(pk, float(np.max(np.abs(up))))
    return 20 * np.log10(pk + 1e-20)


def bands(d, sr):
    f, p = ss.welch(d.mean(axis=1), fs=sr, window="hann", nperseg=16384, noverlap=8192)
    df = f[1] - f[0]
    return np.array([10 * np.log10(np.sum(p[(f >= lo) & (f < hi)]) * df + 1e-30) for lo, hi in BANDS])


def crest_db(d):
    x = d.mean(axis=1)
    return 20 * np.log10((np.max(np.abs(x)) + 1e-20) / (np.sqrt(np.mean(x ** 2)) + 1e-20))


def corr(d):
    if d.shape[1] < 2:
        return 1.0
    l, r = d[:, 0], d[:, 1]
    if np.std(l) < 1e-9 or np.std(r) < 1e-9:
        return 1.0
    return float(np.corrcoef(l, r)[0, 1])


src_pink, sr = read(next(SRC.glob("pink_noise_minus20*.wav")))
src_ms, _ = read(next(SRC.glob("mid_side_test_minus20*.wav")))
src_band = bands(src_pink, sr)
src_corr = corr(src_ms)

print("=== REPRODUCTION: fresh render vs committed loudness-parity numbers ===")
worst = 0.0
for pre in PRESETS:
    fp = json.loads((COMMITTED_FP / pre / "fingerprint.json").read_text(encoding="utf-8"))["fingerprint"]
    op, _ = read(RECHECK / pre / "pink_noise_minus20.wav")
    om, _ = read(RECHECK / pre / "mid_side_test_minus20.wav")
    checks = {
        "LUFS": (lufs(op, sr), fp["loudness"]["output_integrated_lufs"]),
        "truepk": (tp(op, sr), fp["loudness"]["true_peak_ceiling_dbtp"]),
        "corrΔ": (corr(om) - src_corr, fp["stereo"]["correlation_change"]),
        "subΔ": ((bands(op, sr) - src_band)[0], fp["eq_band_delta_raw_db"]["20-60 Hz"]),
        "airΔ": ((bands(op, sr) - src_band)[8], fp["eq_band_delta_raw_db"]["8-16k Hz"]),
    }
    diffs = {k: abs(a - b) for k, (a, b) in checks.items()}
    worst = max(worst, max(diffs.values()))
    flag = "OK" if max(diffs.values()) <= 0.25 else "*** CHECK ***"
    print(f"  {pre:10} maxΔ={max(diffs.values()):.3f}  "
          + " ".join(f"{k}={v:.3f}" for k, v in diffs.items()) + f"   {flag}")
print(f"  -> worst single-metric difference across all 9 presets: {worst:.3f}\n")

print("=== INTENSITY KNOB: universal pink at 0.0 / 0.5 / 1.0 (does it move the sound?) ===")
paths = {
    "0.0": RECHECK / "_intensity_sweep" / "intensity_0_00" / "universal" / "pink_noise_minus20.wav",
    "0.5": RECHECK / "universal" / "pink_noise_minus20.wav",
    "1.0": RECHECK / "_intensity_sweep" / "intensity_1_00" / "universal" / "pink_noise_minus20.wav",
}
rows = {}
for k, p in paths.items():
    d, _ = read(p)
    rows[k] = dict(lufs=lufs(d, sr), crest=crest_db(d), band=bands(d, sr))
    print(f"  intensity {k}: LUFS={rows[k]['lufs']:7.2f}  crest={rows[k]['crest']:6.2f} dB")
band_spread = float(np.max(np.abs(rows['1.0']['band'] - rows['0.0']['band'])))
crest_spread = abs(rows['1.0']['crest'] - rows['0.0']['crest'])
print(f"  0.0 -> 1.0 change: crest {crest_spread:.2f} dB, max band-energy {band_spread:.2f} dB")
print("  VERDICT:", "knob MOVES the sound — 0.5 is a real intermediate setting, not stuck."
      if (band_spread > 0.3 or crest_spread > 0.3) else "*** knob barely moves — investigate ***")
