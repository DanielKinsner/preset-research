"""
Ground-truth registry for the 8 spectrally-neutral test signals.

These specs are the *fixed scientific constants* of this repo. The expected
values below were confirmed empirically by measuring the committed source WAVs
(see tools/_probe findings / reports/validation), not assumed from a spec sheet.

Every downstream tool (validation, fingerprinting, reporting) imports this
module so there is exactly one source of truth for "what each signal is".
"""

# Frequencies in the tone ladder, in order. Each tone is held 3 s, the whole
# ladder repeats twice (20 segments total over 60 s).
TONE_LADDER_FREQS_HZ = [40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 16000]

# Nine analysis bands (Hz). Used for per-band spectral-energy deltas.
SPECTRAL_BANDS = [
    ("20-60 Hz",     20,    60),
    ("60-120 Hz",    60,    120),
    ("120-250 Hz",   120,   250),
    ("250-500 Hz",   250,   500),
    ("500-1k Hz",    500,   1000),
    ("1-2k Hz",      1000,  2000),
    ("2-4k Hz",      2000,  4000),
    ("4-8k Hz",      4000,  8000),
    ("8-16k Hz",     8000,  16000),
]

# Common format spec shared by all 8 signals.
_FORMAT = dict(sample_rate=44100, channels=2, bit_depth="PCM_16",
               frames=2646000, duration_sec=60.0)

# Registry. `role` selects the signal-specific analyzer in audio_metrics.
# `expected` holds the values the validator asserts against, with tolerances.
SIGNALS = {
    "pink_noise_minus20.wav": {
        "role": "pink_noise",
        "purpose": "Primary tonal reference. Equal energy per octave; output delta IS the EQ curve.",
        "priority": 1,
        "expected": {**_FORMAT,
                     "rms_dbfs": -21.0, "rms_tol": 0.5,
                     "lufs_approx": -20.0,
                     "slope_db_per_oct": -3.01, "slope_tol": 0.3,
                     "stereo_decorrelated": True},
    },
    "pink_noise_minus14.wav": {
        "role": "pink_noise",
        "purpose": "Level-dependent check. Spectral delta vs -20 reveals level-dependent processing.",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -15.0, "rms_tol": 0.5,
                     "lufs_approx": -14.0,
                     "slope_db_per_oct": -3.01, "slope_tol": 0.3,
                     "stereo_decorrelated": True},
    },
    "pink_noise_minus10.wav": {
        "role": "pink_noise",
        "purpose": "Hot-level behavior. Pushes compressor/limiter; reveals stand-down on loud material.",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -11.0, "rms_tol": 0.5,
                     "lufs_approx": -10.0,
                     "slope_db_per_oct": -3.01, "slope_tol": 0.3,
                     "stereo_decorrelated": True},
    },
    "sine_sweep_minus20.wav": {
        "role": "sweep",
        "purpose": "Precise frequency response. Reveals narrow-band features broadband noise misses.",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -21.0, "rms_tol": 0.6,
                     "sweep_start_hz": 20, "sweep_end_hz": 20000},
    },
    "click_track.wav": {
        "role": "click_track",
        "purpose": "Compressor timing. Attack, release, transient shaping.",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -44.0, "rms_tol": 1.5,
                     "n_impulses": 120,
                     "impulse_period_ms": 500.0, "period_tol_ms": 1.0,
                     "impulse_spacing_samples": 22050},
    },
    "tone_ladder_minus20.wav": {
        "role": "tone_ladder",
        "purpose": "Discrete per-frequency gain. Exact dB at known frequencies.",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -21.0, "rms_tol": 0.5,
                     "tone_freqs_hz": TONE_LADDER_FREQS_HZ,
                     "tone_seg_sec": 3.0, "tone_reps": 2,
                     "tone_level_dbfs": -21.0,
                     "freq_tol_pct": 2.0, "level_spread_tol_db": 1.0},
    },
    "dynamic_test_minus14.wav": {
        "role": "dynamic",
        "purpose": "Dynamic range preservation. Maintains 20 dB contrast or crushes it?",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -14.0, "rms_tol": 1.0,
                     "segment_sec": 5.0,
                     "loud_dbfs": -14.0, "quiet_dbfs": -34.0,
                     "loud_tol": 1.5, "quiet_tol": 2.0,
                     "contrast_db": 20.0, "contrast_min_db": 18.0},
    },
    "mid_side_test_minus20.wav": {
        "role": "mid_side",
        "purpose": "Stereo width. Narrowing, widening, or rebalancing?",
        "priority": 2,
        "expected": {**_FORMAT,
                     "rms_dbfs": -21.0, "rms_tol": 0.5,
                     "correlation_min": 0.90,
                     "side_minus_mid_db": -24.0, "side_mid_tol": 3.0},
    },
}

# Filename-stem -> role, for matching competitor outputs back to their source
# signal regardless of any suffix the mastering service appends.
SIGNAL_STEMS = {fn.rsplit(".", 1)[0]: fn for fn in SIGNALS}


def role_for(filename: str) -> str | None:
    """Return the analyzer role for a known signal filename, else None."""
    spec = SIGNALS.get(filename)
    return spec["role"] if spec else None


def match_source(output_filename: str) -> str | None:
    """
    Map a competitor output filename back to its source signal filename by
    looking for a known source stem as a substring (case-insensitive).
    e.g. 'pink_noise_minus20_BandLab_Master.wav' -> 'pink_noise_minus20.wav'.
    """
    name = output_filename.lower()
    # Longest stem first so 'pink_noise_minus20' wins over a shorter accidental hit.
    for stem in sorted(SIGNAL_STEMS, key=len, reverse=True):
        if stem.lower() in name:
            return SIGNAL_STEMS[stem]
    return None
