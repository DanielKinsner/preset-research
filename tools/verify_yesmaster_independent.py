"""Independent re-measurement of YES Master outputs — does NOT import the project's
audio_metrics/fingerprint code. Re-derives the load-bearing numbers straight from the
committed WAVs with fresh DSP, then compares to Codex's committed fingerprint JSON.

Purpose: catch a broken MEASUREMENT (not a broken capture). If these match to rounding,
Codex's fingerprint numbers faithfully reflect the audio he committed.
"""
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
SET = ROOT / "competitors" / "yesmaster-loudness-parity"   # the BandLab-comparable set
FP = ROOT / "measurements" / "fingerprints" / "yesmaster-loudness-parity"

BANDS = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
         (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]
BAND_KEYS = ["20-60 Hz", "60-120 Hz", "120-250 Hz", "250-500 Hz", "500-1k Hz",
             "1-2k Hz", "2-4k Hz", "4-8k Hz", "8-16k Hz"]


def read(p):
    data, sr = sf.read(str(p), always_2d=True)
    return data.astype(np.float64), sr


def lufs(data, sr):
    return float(pyln.Meter(sr).integrated_loudness(data))


def true_peak_dbtp(data, sr):
    peak = 0.0
    for ch in range(data.shape[1]):
        x = data[:, ch]
        pad = 64
        xp = np.pad(x, pad, mode="edge")
        up = ss.resample_poly(xp, 4, 1)
        core = up[pad * 4:-pad * 4]
        peak = max(peak, float(np.max(np.abs(core))))
    return 20 * np.log10(peak + 1e-20)


def band_db(data, sr):
    mono = data.mean(axis=1)
    f, pxx = ss.welch(mono, fs=sr, window="hann", nperseg=16384, noverlap=8192)
    df = f[1] - f[0]
    out = []
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        out.append(10 * np.log10(np.sum(pxx[m]) * df + 1e-30))
    return np.array(out)


def corr(data):
    if data.shape[1] < 2:
        return 1.0
    l, r = data[:, 0], data[:, 1]
    if np.std(l) < 1e-9 or np.std(r) < 1e-9:
        return 1.0
    return float(np.corrcoef(l, r)[0, 1])


def src_path(name):
    hits = list(SRC.glob(f"{name}*.wav"))
    return hits[0] if hits else None


def committed(preset):
    return json.loads((FP / preset / "fingerprint.json").read_text(encoding="utf-8"))["fingerprint"]


def line(label, mine, theirs, tol):
    d = abs(mine - theirs)
    flag = "OK " if d <= tol else "*** MISMATCH ***"
    print(f"    {label:24} mine={mine:8.3f}  committed={theirs:8.3f}  Δ={d:6.3f}  {flag}")
    return d <= tol


presets = ["spatial", "oomph", "custom", "punch", "universal"]
src_pink, sr = read(src_path("pink_noise_minus20"))
src_ms, _ = read(src_path("mid_side_test_minus20"))
src_pink_band = band_db(src_pink, sr)
src_ms_corr = corr(src_ms)

print(f"Source pink_-20 LUFS={lufs(src_pink, sr):.3f}  mid_side input corr={src_ms_corr:.3f}\n")

allok = True
for pre in presets:
    print(f"=== {pre} ===")
    fp = committed(pre)
    out_pink, _ = read(SET / pre / "pink_noise_minus20.wav")
    out_ms, _ = read(SET / pre / "mid_side_test_minus20.wav")

    allok &= line("output LUFS (pink)", lufs(out_pink, sr),
                  fp["loudness"]["output_integrated_lufs"], 0.3)
    allok &= line("output true-peak dBTP", true_peak_dbtp(out_pink, sr),
                  fp["loudness"]["true_peak_ceiling_dbtp"], 0.4)
    allok &= line("stereo corr change", corr(out_ms) - src_ms_corr,
                  fp["stereo"]["correlation_change"], 0.03)

    out_band = band_db(out_pink, sr)
    raw_delta = out_band - src_pink_band
    sub_ok = line("sub 20-60 raw delta", raw_delta[0],
                  fp["eq_band_delta_raw_db"]["20-60 Hz"], 0.6)
    air_ok = line("air 8-16k raw delta", raw_delta[8],
                  fp["eq_band_delta_raw_db"]["8-16k Hz"], 0.6)
    allok &= sub_ok & air_ok
    print()

print("OVERALL:", "ALL MATCH — Codex's measurements are faithful to the audio."
      if allok else "*** AT LEAST ONE MISMATCH — investigate ***")
