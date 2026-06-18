"""Generate a stereo WIDTH probe for the test battery.

The existing stereo signal (mid_side_test) is near-mono (side ~24 dB below mid), which
makes it blind to M/S width processing: scaling a near-zero side changes nothing. This
probe is partially-correlated pink noise (L/R correlation ~0.5) so that BOTH widening
(side up -> correlation down) and narrowing (side down -> correlation up) are clearly
measurable. Pink spectrum keeps it spectrally neutral like the rest of the battery.

Deterministic (seeded) so it reproduces exactly. 44.1 kHz / 16-bit / stereo / 60.000 s.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
SR = 44100
DUR = 60.0
N = int(SR * DUR)
OUT = Path(__file__).resolve().parent.parent / "source" / "test-signals" / "stereo_field_minus20.wav"


def pink(rng):
    """One channel of unit-variance pink noise via 1/sqrt(f) spectral shaping."""
    w = rng.standard_normal(N)
    spec = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(N, d=1.0 / SR)
    scale = np.ones_like(freqs)
    scale[1:] = 1.0 / np.sqrt(freqs[1:])
    x = np.fft.irfft(spec * scale, n=N)
    return x / np.std(x)


def main():
    rng = np.random.default_rng(20260618)
    common, ind_l, ind_r = pink(rng), pink(rng), pink(rng)
    # equal weight on shared vs independent -> corr = var(common)/var(L) = 1/2
    left = common + ind_l
    right = common + ind_r

    target_rms = 10 ** (-20.0 / 20.0)  # -20 dBFS RMS
    cur_rms = np.sqrt(np.mean(np.concatenate([left, right]) ** 2))
    g = target_rms / cur_rms
    left *= g
    right *= g

    corr = float(np.corrcoef(left, right)[0, 1])
    rms_db = 20 * np.log10(np.sqrt(np.mean(np.concatenate([left, right]) ** 2)))
    peak_db = 20 * np.log10(max(np.max(np.abs(left)), np.max(np.abs(right))))
    data = np.column_stack([left, right]).astype(np.float32)
    sf.write(str(OUT), data, SR, subtype="PCM_16")
    print(f"wrote {OUT.name}: {DUR}s {SR}Hz stereo 16-bit")
    print(f"  L/R correlation = {corr:.3f}  (target ~0.5)")
    print(f"  RMS = {rms_db:.2f} dBFS   peak = {peak_db:.2f} dBFS")


if __name__ == "__main__":
    main()
