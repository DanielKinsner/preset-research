"""
Core audio-measurement library for preset fingerprinting.

Design goals
------------
* Accurate, standards-based numbers (EBU R128 loudness via pyloudnorm,
  ITU-R BS.1770-style true-peak via 4x oversampling).
* One `measure_file()` entry point that returns a fully structured, JSON-able
  dict — the canonical per-file record consumed by both validation and
  fingerprinting. No measurement logic lives in the scripts; they only
  orchestrate and compare.
* Pure functions on float64 arrays so each metric is independently testable.

All amplitudes are linear in [-1, 1]; "dBFS" means 20*log10(x) with full scale
= 1.0 (so a full-scale sine reads -3.01 dBFS RMS, 0 dBFS peak).
"""
from __future__ import annotations

import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal

import signals as sig_registry

EPS = 1e-20
_METERS: dict[int, pyln.Meter] = {}


# --------------------------------------------------------------------------- #
# Loading & basic helpers
# --------------------------------------------------------------------------- #
def db(x) -> float:
    """Linear amplitude -> dB (20*log10). Scalar or array-safe min floor."""
    return float(20.0 * np.log10(np.maximum(np.abs(x), EPS)))


def _power_db(p) -> float:
    """Linear power -> dB (10*log10)."""
    return float(10.0 * np.log10(np.maximum(p, EPS)))


def load_audio(path) -> dict:
    """
    Load a WAV as float64 in [-1, 1], always 2-D [frames, channels].
    Returns data plus authoritative format metadata read from the header.
    """
    info = sf.info(str(path))
    data, sr = sf.read(str(path), always_2d=True, dtype="float64")
    return {
        "data": data,
        "sample_rate": sr,
        "channels": data.shape[1],
        "frames": data.shape[0],
        "duration_sec": data.shape[0] / sr,
        "bit_depth": info.subtype,           # e.g. PCM_16, PCM_24, FLOAT
        "format": info.format,
    }


def _meter(sr: int) -> pyln.Meter:
    if sr not in _METERS:
        _METERS[sr] = pyln.Meter(sr)
    return _METERS[sr]


def _mono(data: np.ndarray) -> np.ndarray:
    """Channel-mean mono sum for spectral analysis."""
    return data.mean(axis=1) if data.ndim > 1 and data.shape[1] > 1 else data.reshape(-1)


def content_onset(mono: np.ndarray, sr: int, thresh_db: float = -50.0,
                  win_ms: float = 10.0) -> int:
    """
    First sample index where audible content begins. Mastering services often
    prepend a short lead-in/silence (BandLab outputs run up to ~0.4 s long), so
    segment-timed analyses (tone ladder, dynamic) must align to real content,
    not to t=0. Clean source signals return ~0 (no change).
    """
    win = max(1, int(win_ms / 1000 * sr))
    n = len(mono) // win
    if n == 0:
        return 0
    frames = mono[:n * win].reshape(n, win)
    rms = np.sqrt(np.mean(np.square(frames), axis=1))
    thr = 10 ** (thresh_db / 20)
    hits = np.where(rms > thr)[0]
    return int(hits[0] * win) if hits.size else 0


# --------------------------------------------------------------------------- #
# Level / loudness metrics
# --------------------------------------------------------------------------- #
def peak_dbfs(data: np.ndarray) -> float:
    return db(np.max(np.abs(data)))


def rms_dbfs(data: np.ndarray) -> float:
    """Broadband RMS in dBFS, energy-POOLED across all channels (full-scale sine
    reads -3.01 dBFS). For asymmetric stereo this sits up to 3 dB below the louder
    channel; pass _mono(data) for a mono-downmix reference."""
    return db(np.sqrt(np.mean(np.square(data))))


def true_peak_dbtp(data: np.ndarray, sr: int, oversample: int = 4, pad: int = 64) -> float:
    """
    ITU-R BS.1770-style true (inter-sample) peak via Nx polyphase oversampling.
    Catches reconstruction overshoots that sample-peak misses — critical for
    judging whether a mastering limiter actually clips on playback.

    The signal is edge-padded before resampling so the polyphase FIR does not ring
    against the implicit zero-padding at the file boundaries — that boundary ringing
    injects a phantom overshoot of up to ~1 dB on material whose first/last sample
    sits near full scale (abrupt start/end, fade-less cut, DC offset). The pad
    region is discarded before taking the max; genuine edge peaks survive because
    edge-padding places them in the interior. Interior inter-sample overshoots
    (e.g. Gibbs at a real step) are unaffected, as intended.
    """
    peak = 0.0
    guard = pad * oversample
    for ch in range(data.shape[1]):
        x = np.pad(data[:, ch], pad, mode="edge")
        up = signal.resample_poly(x, oversample, 1)
        core = up[guard:-guard] if up.shape[0] > 2 * guard else up
        peak = max(peak, float(np.max(np.abs(core))))
    return db(peak)


def crest_factor_db(data: np.ndarray) -> float:
    """Peak-to-RMS ratio in dB. High = punchy/dynamic, low = compressed/dense."""
    return peak_dbfs(data) - rms_dbfs(data)


def loudness_metrics(data: np.ndarray, sr: int) -> dict:
    """Integrated loudness (LUFS) and loudness range (LRA, LU) per EBU R128."""
    m = _meter(sr)
    integrated = float(m.integrated_loudness(data))
    try:
        lra = float(m.loudness_range(data))
    except (ValueError, IndexError) as e:
        # pyloudnorm raises on sub-block-size / degenerate material. Record NaN but
        # don't silently swallow unrelated failures (wrong rate, API change).
        import warnings
        warnings.warn(f"loudness_range failed ({type(e).__name__}: {e}); LRA set to NaN")
        lra = float("nan")
    return {"integrated_lufs": integrated, "lra_lu": lra}


# --------------------------------------------------------------------------- #
# Spectral metrics
# --------------------------------------------------------------------------- #
def _welch_psd(mono: np.ndarray, sr: int, nperseg: int = 16384):
    nperseg = min(nperseg, len(mono))
    f, pxx = signal.welch(mono, sr, nperseg=nperseg, noverlap=nperseg // 2,
                          window="hann", detrend=False)
    return f, pxx


def band_energy_dbfs(data: np.ndarray, sr: int,
                     bands=sig_registry.SPECTRAL_BANDS) -> dict:
    """
    Per-band energy as a dBFS-equivalent level: 10*log10 of each band's
    contribution to mean-square (sum of PSD * df), on the MONO downmix over
    20 Hz-16 kHz. NOTE: these absolute band levels do NOT sum to the full-file
    stereo RMS — the mono downmix discards decorrelated side energy and the bands
    omit sub-20 Hz and 16k-Nyquist, so the sum can sit ~6 dB below rms_dbfs on
    decorrelated pink. Only the per-band DELTAS (output - input) are
    makeup-gain-comparable: input and output pass the identical downmix so the
    offset cancels.
    """
    mono = _mono(data)
    f, pxx = _welch_psd(mono, sr)
    df = f[1] - f[0]
    out = {}
    for name, lo, hi in bands:
        mask = (f >= lo) & (f < hi)
        power = float(np.sum(pxx[mask]) * df)
        out[name] = _power_db(power)
    return out


def spectral_slope_db_per_oct(data: np.ndarray, sr: int,
                              fmin: float = 50.0, fmax: float = 16000.0,
                              n_points: int = 96) -> float:
    """
    Least-squares slope of PSD (dB) vs log-frequency, expressed per octave.
    Pink noise -> ~-3.01 dB/oct; white -> 0; a brightening master -> less negative.

    The PSD is resampled onto a LOG-UNIFORM frequency grid before fitting. Welch
    bins are linearly spaced in Hz, so a raw log-f fit gives the top octaves ~2x
    the bins and weights HF ~5-6x more than LF per dB — which made the tilt
    understate bass moves relative to equal treble moves. Equal weight per octave
    removes that bias (an ideal power law reads its true slope either way).
    """
    mono = _mono(data)
    f, pxx = _welch_psd(mono, sr)
    mask = (f >= fmin) & (f <= fmax) & (pxx > 0)
    if int(mask.sum()) < 2:
        return float("nan")
    logf = np.log10(f[mask])
    ydb = 10.0 * np.log10(pxx[mask])
    grid = np.linspace(logf.min(), logf.max(), n_points)   # uniform in log-frequency
    ydb_u = np.interp(grid, logf, ydb)
    slope_per_decade, _ = np.polyfit(grid, ydb_u, 1)
    return float(slope_per_decade * np.log10(2.0))  # per-decade -> per-octave


def spectral_centroid_hz(data: np.ndarray, sr: int) -> float:
    """Power-weighted mean frequency. Rises when a master adds brightness."""
    mono = _mono(data)
    f, pxx = _welch_psd(mono, sr)
    mask = (f >= 20) & (f <= 20000)
    num = float(np.sum(f[mask] * pxx[mask]))
    den = float(np.sum(pxx[mask]))
    return num / den if den > 0 else float("nan")


# --------------------------------------------------------------------------- #
# Stereo metrics
# --------------------------------------------------------------------------- #
def stereo_metrics(data: np.ndarray) -> dict:
    """L-R correlation, mid/side RMS, and side-minus-mid width indicator."""
    if data.shape[1] < 2:
        return {"correlation": 1.0, "mid_rms_dbfs": rms_dbfs(data),
                "side_rms_dbfs": float("-inf"), "side_minus_mid_db": float("-inf"),
                "mono": True}
    L, R = data[:, 0], data[:, 1]
    corr = float(np.corrcoef(L, R)[0, 1]) if np.std(L) > 0 and np.std(R) > 0 else 1.0
    mid = (L + R) / 2.0
    side = (L - R) / 2.0
    mid_db, side_db = rms_dbfs(mid), rms_dbfs(side)
    return {"correlation": corr, "mid_rms_dbfs": mid_db, "side_rms_dbfs": side_db,
            "side_minus_mid_db": side_db - mid_db, "mono": False}


# --------------------------------------------------------------------------- #
# Signal-specific analyzers
# --------------------------------------------------------------------------- #
def _dominant_freq(seg: np.ndarray, sr: int) -> float:
    """Peak-bin frequency with parabolic interpolation for sub-bin accuracy."""
    w = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(w))
    k = int(np.argmax(spec))
    if 0 < k < len(spec) - 1:
        a, b, c = spec[k - 1], spec[k], spec[k + 1]
        denom = (a - 2 * b + c)
        delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
    else:
        delta = 0.0
    return float((k + delta) * sr / len(seg))


def analyze_tone_ladder(data: np.ndarray, sr: int,
                        expected_freqs=sig_registry.TONE_LADDER_FREQS_HZ,
                        seg_sec: float = 3.0, reps: int = 2,
                        guard: float = 0.25) -> dict:
    """
    Per-tone frequency + level. Analyzes the steady middle of each segment
    (skipping `guard` s at each edge) so any ramp the service applies is excluded.
    For an output master, `level_dbfs` per tone IS the per-frequency gain when
    differenced against the input.
    """
    mono = _mono(data)
    seg = int(seg_sec * sr)
    g = int(guard * sr)
    onset = content_onset(mono, sr)            # align to real content (services prepend lead-in)
    tones = []
    # cap at the schedule length so a long trailing tail can't emit a spurious
    # 21st (unscheduled) segment that would skew level_spread_db.
    n_seg = min(max(0, (len(mono) - onset) // seg), reps * len(expected_freqs))
    schedule = (expected_freqs * reps)[:n_seg]
    for i in range(n_seg):
        chunk = mono[onset + i * seg + g: onset + (i + 1) * seg - g]
        if len(chunk) < 64:
            continue
        tones.append({
            "index": i,
            "t_start_sec": round((onset + i * seg) / sr, 3),
            "expected_hz": schedule[i] if i < len(schedule) else None,
            "measured_hz": round(_dominant_freq(chunk, sr), 2),
            "level_dbfs": round(rms_dbfs(chunk), 3),
        })
    levels = [t["level_dbfs"] for t in tones]
    return {"tones": tones,
            "onset_sec": round(onset / sr, 3),
            "level_spread_db": round(max(levels) - min(levels), 3) if levels else None,
            "n_segments": len(tones)}


def analyze_click_track(data: np.ndarray, sr: int,
                        period_sec: float = 0.5, thresh_ratio: float = 0.3) -> dict:
    """
    Detect impulse onsets and their spacing/width/peak. For an input this
    validates structure; for an output the same onsets anchor attack/release
    measurement (see fingerprint.click_envelope).
    """
    mono = _mono(data)
    env = np.abs(mono)
    thr = float(np.max(env)) * thresh_ratio
    above = np.where(env > thr)[0]
    if len(above) == 0:
        return {"n_impulses": 0, "impulses": [], "mean_spacing_samples": None,
                "mean_period_ms": None, "mean_peak_dbfs": None}
    groups = np.split(above, np.where(np.diff(above) > int(0.05 * sr))[0] + 1)
    onsets, widths, peaks = [], [], []
    for grp in groups:
        seg = env[grp[0]:grp[-1] + 1]
        onsets.append(int(grp[0]))
        widths.append(int(grp[-1] - grp[0] + 1))
        peaks.append(float(np.max(seg)))
    spacing = np.diff(onsets) if len(onsets) > 1 else np.array([])
    return {
        "n_impulses": len(onsets),
        "mean_spacing_samples": float(np.mean(spacing)) if spacing.size else None,
        "mean_period_ms": float(np.mean(spacing) / sr * 1000) if spacing.size else None,
        "mean_width_samples": float(np.mean(widths)),
        "mean_peak_dbfs": round(db(np.mean(peaks)), 3),
        "first_onset_sample": onsets[0],
    }


def analyze_dynamic(data: np.ndarray, sr: int, segment_sec: float = 5.0) -> dict:
    """
    Per-segment RMS, split into loud/quiet by the median, with the loud-quiet
    contrast in dB. A preset that 'crushes' dynamics shrinks this contrast.
    """
    mono = _mono(data)
    seg = int(segment_sec * sr)
    onset = content_onset(mono, sr)   # align to real content (services prepend lead-in)
    segs = []
    for i in range((len(mono) - onset) // seg):
        chunk = mono[onset + i * seg: onset + (i + 1) * seg]
        segs.append({"index": i, "t_start_sec": round((onset + i * seg) / sr, 3),
                     "rms_dbfs": round(rms_dbfs(chunk), 3)})
    levels = np.array([s["rms_dbfs"] for s in segs])
    if len(levels) == 0:
        return {"segments": [], "contrast_db": None}
    med = float(np.median(levels))
    loud = levels[levels >= med]
    quiet = levels[levels < med]
    loud_mean = float(np.mean(loud)) if loud.size else None
    quiet_mean = float(np.mean(quiet)) if quiet.size else None
    contrast = (loud_mean - quiet_mean) if (loud_mean is not None and quiet_mean is not None) else None
    return {"segments": segs,
            "onset_sec": round(onset / sr, 3),
            "loud_mean_dbfs": round(loud_mean, 3) if loud_mean is not None else None,
            "quiet_mean_dbfs": round(quiet_mean, 3) if quiet_mean is not None else None,
            "contrast_db": round(contrast, 3) if contrast is not None else None,
            "n_segments": len(segs)}


def analyze_mid_side(data: np.ndarray, sr: int) -> dict:
    """Correlation + mid/side balance, the stereo-width fingerprint dimensions."""
    return stereo_metrics(data)


def analyze_sweep(data: np.ndarray, sr: int) -> dict:
    """
    Coarse swept-frequency response via STFT: track band-limited energy over
    time. For validation we confirm energy spans low->high across the file.
    Fine deconvolved response is computed in fingerprinting against the input.
    """
    mono = _mono(data)
    f, t, Zxx = signal.stft(mono, sr, nperseg=4096, noverlap=2048)
    mag = np.abs(Zxx)
    # dominant frequency over time
    dom = f[np.argmax(mag, axis=0)]
    valid = dom[mag.max(axis=0) > mag.max() * 0.01]
    return {"dominant_start_hz": round(float(valid[0]), 1) if valid.size else None,
            "dominant_end_hz": round(float(valid[-1]), 1) if valid.size else None,
            "monotonic_fraction": round(float(np.mean(np.diff(valid) >= 0)), 3) if valid.size > 1 else None}


_ANALYZERS = {
    "tone_ladder": analyze_tone_ladder,
    "click_track": analyze_click_track,
    "dynamic": analyze_dynamic,
    "mid_side": analyze_mid_side,
    "sweep": analyze_sweep,
}


# --------------------------------------------------------------------------- #
# Canonical per-file measurement
# --------------------------------------------------------------------------- #
def measure_file(path, role: str | None = None) -> dict:
    """
    Full canonical measurement of one WAV. `role` (from signals.SIGNALS) selects
    a signal-specific analyzer; if None it's inferred from the filename.
    Returns a JSON-serialisable dict — the unit of record for this repo.
    """
    from pathlib import Path
    path = Path(path)
    if role is None:
        role = sig_registry.role_for(path.name)

    a = load_audio(path)
    data, sr = a["data"], a["sample_rate"]

    rec = {
        "file": path.name,
        "role": role,
        "format": {
            "sample_rate": sr,
            "channels": a["channels"],
            "bit_depth": a["bit_depth"],
            "frames": a["frames"],
            "duration_sec": round(a["duration_sec"], 4),
        },
        "levels": {
            "peak_dbfs": round(peak_dbfs(data), 3),
            "true_peak_dbtp": round(true_peak_dbtp(data, sr), 3),
            "rms_dbfs": round(rms_dbfs(data), 3),
            # mono-downmix RMS — the reference EQ-shape normalization must use so it
            # matches the (mono) band energies; rms_dbfs above is the stereo pool.
            "rms_mono_dbfs": round(rms_dbfs(_mono(data)), 3),
            "crest_factor_db": round(crest_factor_db(data), 3),
        },
        "loudness": {k: round(v, 3) for k, v in loudness_metrics(data, sr).items()},
        "spectral": {
            "centroid_hz": round(spectral_centroid_hz(data, sr), 2),
            "slope_db_per_oct": round(spectral_slope_db_per_oct(data, sr), 3),
            "bands_dbfs": {k: round(v, 3) for k, v in band_energy_dbfs(data, sr).items()},
        },
        "stereo": {k: (round(v, 4) if isinstance(v, float) else v)
                   for k, v in stereo_metrics(data).items()},
    }
    if role in _ANALYZERS:
        rec["signal_specific"] = _ANALYZERS[role](data, sr)
    return rec
