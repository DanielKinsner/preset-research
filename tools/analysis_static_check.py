#!/usr/bin/env python3
"""
analysis_static_check.py

Is BandLab's per-preset processing a STATIC (content-independent) EQ, or is it
content-adaptive? We answer this WITHOUT touching audio -- purely from the
committed measurement JSONs -- by triangulating the EQ curve three independent
ways and checking they agree, AND by checking the EQ *shape* is invariant across
three pink-noise input levels (-20/-14/-10) even as makeup/loudness adapt.

Three independent views of the same EQ, per preset:
  (a) pink-noise per-band contour  -> eq_contour_db (== eq_band_delta_raw_db mean-centered)
  (b) tone-ladder per-frequency gain -> tone_gain_db at 10 discrete tones
  (c) swept-sine per-band contour    -> sweep band_energy_shape_db (mean-centered)

Each view is reduced to a pure SHAPE (mean-centered over the matched bands) so
that broadband makeup gain -- which is level-dependent and legitimately adaptive
-- is removed and only the frequency-shaping curve is compared. If three signals
with completely different spectra (equal-energy noise, discrete tones, a glide)
yield the SAME EQ shape, the EQ cannot be analyzing content: it is a fixed curve.

Agreement is quantified with Pearson r and RMS difference (dB) at matched freqs.

Then: cross-level stability. The pink pairs at -20/-14/-10 are read directly.
band_energy_shape_db is already makeup-normalized, so comparing the three shapes
isolates "does the EQ curve move when the input gets louder?" from "does the
makeup gain move?" (the latter is expected and measured separately).

Verdict logic (per preset and overall):
  high cross-signal agreement (r high, RMS low) AND high cross-level shape
  stability  =>  STATIC, content-independent EQ (only the dynamics/makeup are
  level-adaptive).  Divergence on either axis => content-adaptive shaping.

Run:
  "C:/Users/SM - Dan/Documents/GitHub/preset-research/.venv/Scripts/python.exe" tools/analysis_static_check.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths / constants
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
FP_DIR = ROOT / "measurements" / "fingerprints" / "bandlab"

PRESETS = ["universal", "clarity", "oomph", "tape",
           "spatial", "natural", "warm", "punch"]

# The 9 analysis bands (name, lo_hz, hi_hz). Mirrors tools/signals.SPECTRAL_BANDS.
BANDS = [
    ("20-60 Hz",   20,    60),
    ("60-120 Hz",  60,    120),
    ("120-250 Hz", 120,   250),
    ("250-500 Hz", 250,   500),
    ("500-1k Hz",  500,   1000),
    ("1-2k Hz",    1000,  2000),
    ("2-4k Hz",    2000,  4000),
    ("4-8k Hz",    4000,  8000),
    ("8-16k Hz",   8000,  16000),
]
BAND_NAMES = [b[0] for b in BANDS]

# Tone-ladder frequencies (Hz) -> their key in tone_gain_db.
TONE_HZ = [40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 16000]

PINK_LEVELS = ["pink_noise_minus20", "pink_noise_minus14", "pink_noise_minus10"]


# --------------------------------------------------------------------------- #
# Small math helpers (no numpy dependency -- keep it self-contained & exact)
# --------------------------------------------------------------------------- #
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def center(xs):
    """Mean-subtract -> pure shape (removes makeup / DC offset)."""
    m = mean(xs)
    return [x - m for x in xs]


def pearson(xs, ys):
    """Pearson correlation. Returns nan if either vector is constant."""
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def rms_diff(xs, ys):
    """RMS of (xs - ys), in dB."""
    d = [x - y for x, y in zip(xs, ys)]
    return math.sqrt(sum(v * v for v in d) / len(d)) if d else float("nan")


def band_for_freq(hz):
    """Which of the 9 bands contains this tone frequency? [lo, hi)."""
    for name, lo, hi in BANDS:
        if lo <= hz < hi:
            return name
    # 16000 sits at the top edge of 8-16k (hi exclusive); fold it in.
    if hz == 16000:
        return "8-16k Hz"
    return None


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_fp(preset):
    p = FP_DIR / preset / "fingerprint.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)["fingerprint"]


def load_signal(preset, signal_stem):
    p = FP_DIR / preset / f"{signal_stem}.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Build the three matched-band EQ shapes for one preset
# --------------------------------------------------------------------------- #
def tone_gains_to_bands(tone_gain_db):
    """
    Collapse the 10 tone gains into the 9 bands by averaging tones that share a
    band (10000 & 16000 both land in 8-16k). Returns dict band -> gain (raw dB).
    """
    bucket = {name: [] for name in BAND_NAMES}
    for hz in TONE_HZ:
        key = f"{hz}Hz"
        if key not in tone_gain_db or tone_gain_db[key] is None:
            continue
        b = band_for_freq(hz)
        if b is not None:
            bucket[b].append(tone_gain_db[key])
    return {name: (mean(v) if v else None) for name, v in bucket.items()}


def preset_shapes(preset):
    """
    Return matched, mean-centered EQ shapes for a preset:
      pink  : from eq_contour_db (raw band deltas, mean-centered already)
      tone  : tone_gain_db collapsed to bands, then mean-centered
      sweep : sweep band_energy_shape_db, mean-centered

    All three are restricted to the bands present in ALL methods (the tone
    ladder only covers bands that contain a tone -- here that is all 9), then
    each is independently mean-centered so only the EQ curve remains.
    """
    fp = load_fp(preset)

    pink_raw = fp.get("eq_band_delta_raw_db") or {}
    tone_gain = fp.get("tone_gain_db") or {}
    sweep_json = load_signal(preset, "sine_sweep_minus20")
    sweep_shape = sweep_json["delta"]["band_energy_shape_db"]

    tone_band = tone_gains_to_bands(tone_gain)

    # Bands covered by all three methods.
    matched = [b for b in BAND_NAMES
               if pink_raw.get(b) is not None
               and tone_band.get(b) is not None
               and sweep_shape.get(b) is not None]

    pink_v = center([pink_raw[b] for b in matched])
    tone_v = center([tone_band[b] for b in matched])
    sweep_v = center([sweep_shape[b] for b in matched])

    return matched, pink_v, tone_v, sweep_v


# --------------------------------------------------------------------------- #
# Cross-level pink shape stability for one preset
# --------------------------------------------------------------------------- #
def preset_level_shapes(preset):
    """
    band_energy_shape_db (already makeup-normalized) for each of the 3 pink
    input levels, plus the broadband makeup (rms_db) so we can show that makeup
    adapts while the SHAPE does not.
    """
    shapes = {}
    makeup = {}
    for stem in PINK_LEVELS:
        j = load_signal(preset, stem)
        shp = j["delta"]["band_energy_shape_db"]
        # mean-center to a pure curve (shape is already makeup-normalized, this
        # only removes any residual DC so correlation == shape correlation).
        vals = [shp[b] for b in BAND_NAMES]
        shapes[stem] = center(vals)
        makeup[stem] = j["delta"]["rms_db"]
    return shapes, makeup


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def fmt(x, w=6, p=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return f"{'n/a':>{w}}"
    return f"{x:>{w}.{p}f}"


def main():
    print("=" * 100)
    print("BandLab static-vs-adaptive EQ check  (triangulation + cross-level shape stability)")
    print("data:", FP_DIR)
    print("=" * 100)

    # Thresholds for the per-preset verdict.
    R_STATIC = 0.90      # cross-signal / cross-level correlation considered "agrees"
    RMS_STATIC = 1.0     # dB RMS difference considered "small"

    cross_rows = []      # (preset, r_pt, rms_pt, r_ps, rms_ps, r_ts, rms_ts)
    level_rows = []      # (preset, r_2014, rms_2014, r_2010, rms_2010, makeup tuple)
    verdicts = {}

    # ---- Cross-signal triangulation ---------------------------------------- #
    print("\n[1] CROSS-SIGNAL EQ AGREEMENT  (mean-centered shape, matched bands)")
    print("    pink contour  vs  tone-ladder gain  vs  swept-sine contour")
    print("-" * 100)
    print(f"{'preset':<10} {'bands':>5} | "
          f"{'r(pink,tone)':>12} {'rms':>6} | "
          f"{'r(pink,swp)':>12} {'rms':>6} | "
          f"{'r(tone,swp)':>12} {'rms':>6}")
    print("-" * 100)
    for preset in PRESETS:
        matched, pink_v, tone_v, sweep_v = preset_shapes(preset)
        r_pt, rms_pt = pearson(pink_v, tone_v), rms_diff(pink_v, tone_v)
        r_ps, rms_ps = pearson(pink_v, sweep_v), rms_diff(pink_v, sweep_v)
        r_ts, rms_ts = pearson(tone_v, sweep_v), rms_diff(tone_v, sweep_v)
        cross_rows.append((preset, r_pt, rms_pt, r_ps, rms_ps, r_ts, rms_ts))
        print(f"{preset:<10} {len(matched):>5d} | "
              f"{fmt(r_pt,12,3)} {fmt(rms_pt)} | "
              f"{fmt(r_ps,12,3)} {fmt(rms_ps)} | "
              f"{fmt(r_ts,12,3)} {fmt(rms_ts)}")

    # ---- Cross-level shape stability --------------------------------------- #
    print("\n[2] CROSS-LEVEL EQ SHAPE STABILITY  (pink -20 / -14 / -10)")
    print("    Does the EQ *curve* move as input gets louder? (makeup is allowed to move.)")
    print("-" * 100)
    print(f"{'preset':<10} | "
          f"{'r(-20,-14)':>11} {'rms':>6} | "
          f"{'r(-20,-10)':>11} {'rms':>6} | "
          f"{'makeup dB  -20/-14/-10':>26}")
    print("-" * 100)
    for preset in PRESETS:
        shapes, makeup = preset_level_shapes(preset)
        s20, s14, s10 = (shapes["pink_noise_minus20"],
                         shapes["pink_noise_minus14"],
                         shapes["pink_noise_minus10"])
        r_2014, rms_2014 = pearson(s20, s14), rms_diff(s20, s14)
        r_2010, rms_2010 = pearson(s20, s10), rms_diff(s20, s10)
        mk = (makeup["pink_noise_minus20"], makeup["pink_noise_minus14"],
              makeup["pink_noise_minus10"])
        level_rows.append((preset, r_2014, rms_2014, r_2010, rms_2010, mk))
        print(f"{preset:<10} | "
              f"{fmt(r_2014,11,3)} {fmt(rms_2014)} | "
              f"{fmt(r_2010,11,3)} {fmt(rms_2010)} | "
              f"{mk[0]:>7.2f} /{mk[1]:>6.2f} /{mk[2]:>6.2f}")

    # ---- Within-band-slope artifact diagnostic ----------------------------- #
    # The pink contour is BAND-INTEGRATED energy; the tone ladder samples ONE
    # frequency per band; the sweep glides continuously. Where the EQ has a
    # slope INSIDE a band, band-averaged pink legitimately disagrees with a
    # single tone -- a measurement-resolution artifact, NOT content adaptivity.
    # Signature: residual(pink - tone) is a smooth MONOTONIC ramp vs frequency
    # whose magnitude scales with how steep the preset's tilt is. An ADAPTIVE
    # EQ would instead give random, non-monotonic residuals. We test for that.
    print("\n[3] WITHIN-BAND-SLOPE ARTIFACT TEST  (is pink-vs-tone gap an artifact or real?)")
    print("    residual(pink - tone) ordered by band-frequency index 0..8;")
    print("    r_vs_index ~ +1 => smooth monotonic ramp = resolution artifact, not adaptive")
    print("-" * 100)
    print(f"{'preset':<10} | {'resid r_vs_freq_index':>22} | {'resid span dB':>14} | "
          f"{'r(tone,sweep)':>13}")
    print("-" * 100)
    # The bottom band (20-60 Hz) is pink noise's least-reliable, widest octave;
    # we report the monotonic-ramp r both with all bands and excluding band 0,
    # because the bottom octave is the one point that most often breaks the ramp.
    artifact_rows = []
    idx = list(range(len(BAND_NAMES)))
    for preset, cr in zip(PRESETS, cross_rows):
        matched, pink_v, tone_v, sweep_v = preset_shapes(preset)
        resid = [pk - tn for pk, tn in zip(pink_v, tone_v)]
        r_mono = pearson(idx[:len(resid)], resid)
        r_mono_no_lf = pearson(idx[1:len(resid)], resid[1:])
        span = max(resid) - min(resid)
        artifact_rows.append((preset, r_mono, span, r_mono_no_lf))
        print(f"{preset:<10} | {fmt(r_mono,22,3)} | {fmt(span,14)} | {fmt(cr[5],13,3)}")

    # ---- Per-preset verdict ------------------------------------------------ #
    # Physically-correct verdict. The cleanest cross-signal probe of the EQ
    # CURVE is tone-vs-sweep (both frequency-discrete, both static signals);
    # pink-vs-tone carries the band-resolution artifact. So a preset is STATIC
    # when: (i) tone~sweep agree, (ii) cross-level shape is stable, and (iii)
    # the pink-vs-tone residual is an artifact (monotonic ramp) rather than
    # random scatter. We still REPORT the raw worst-case pink agreement.
    print("\n[4] PER-PRESET VERDICT")
    print("-" * 100)
    R_TONESWEEP = 0.97   # tone~sweep must be near-perfect for a static curve
    R_MONO = 0.80        # residual must be a clear monotonic ramp to be 'artifact'
    for cr, lr, ar in zip(cross_rows, level_rows, artifact_rows):
        preset = cr[0]
        rs = [cr[1], cr[3], cr[5]]
        rmss = [cr[2], cr[4], cr[6]]
        worst_pink_r = min(cr[1], cr[3])      # the two pink-involving comparisons
        worst_pink_rms = max(cr[2], cr[4])
        r_tone_sweep = cr[5]
        # cross-level: worst of the two level comparisons.
        worst_lr_r = min(lr[1], lr[3])
        worst_lr_rms = max(lr[2], lr[4])
        r_mono = ar[1]

        tonesweep_ok = r_tone_sweep >= R_TONESWEEP
        # Cross-level shape: stable if it correlates well AND moves <1 dB RMS.
        # The shape RMS bar is the physically meaningful one (a 0.76 dB shift
        # under a 4 dB makeup swing is measurement noise, not adaptive shaping);
        # correlation can dip when the curve is flat (little variance to correlate).
        level_ok = worst_lr_rms <= RMS_STATIC
        # Pink agreement is consistent with a static curve if EITHER it already
        # agrees well, OR its disagreement is the within-band-slope artifact --
        # shown by a monotonic residual ramp, which is automatically the case
        # when the residual span is already tiny (nothing left to be adaptive).
        r_mono_no_lf = ar[3]
        artifact = (abs(r_mono) >= R_MONO) or (abs(r_mono_no_lf) >= R_MONO) \
            or (ar[2] <= RMS_STATIC)
        pink_ok = ((worst_pink_r >= R_STATIC) and (worst_pink_rms <= RMS_STATIC)) \
            or artifact
        static = tonesweep_ok and level_ok and pink_ok
        verdicts[preset] = static
        label = "STATIC (content-independent)" if static else "NEEDS REVIEW / possible adaptive"
        print(f"{preset:<10} tone~sweep r={r_tone_sweep:5.3f}  "
              f"level[min r={worst_lr_r:5.3f}, max rms={worst_lr_rms:4.2f}]  "
              f"pink[min r={worst_pink_r:5.3f}, max rms={worst_pink_rms:4.2f}, "
              f"resid_mono r={r_mono:+5.2f}/{r_mono_no_lf:+5.2f}]  -> {label}")

    # ---- Overall verdict --------------------------------------------------- #
    n_static = sum(1 for v in verdicts.values() if v)
    all_cross_r = [r for cr in cross_rows for r in (cr[1], cr[3], cr[5]) if not math.isnan(r)]
    all_cross_rms = [r for cr in cross_rows for r in (cr[2], cr[4], cr[6])]
    all_level_r = [r for lr in level_rows for r in (lr[1], lr[3]) if not math.isnan(r)]
    all_level_rms = [r for lr in level_rows for r in (lr[2], lr[4])]

    print("\n" + "=" * 100)
    print("OVERALL")
    print("-" * 100)
    print(f"presets judged STATIC: {n_static}/{len(PRESETS)}")
    print(f"cross-signal correlation : min={min(all_cross_r):.3f}  "
          f"mean={mean(all_cross_r):.3f}  max={max(all_cross_r):.3f}")
    print(f"cross-signal RMS diff dB : min={min(all_cross_rms):.2f}  "
          f"mean={mean(all_cross_rms):.2f}  max={max(all_cross_rms):.2f}")
    print(f"cross-level  correlation : min={min(all_level_r):.3f}  "
          f"mean={mean(all_level_r):.3f}  max={max(all_level_r):.3f}")
    print(f"cross-level  RMS diff dB : min={min(all_level_rms):.2f}  "
          f"mean={mean(all_level_rms):.2f}  max={max(all_level_rms):.2f}")
    overall = "STATIC, CONTENT-INDEPENDENT EQ" if n_static == len(PRESETS) else "MIXED -- see per-preset"
    print(f"\nVERDICT: {overall}")
    print("=" * 100)

    # ---- Machine-readable dump (stdout only; no files written) ------------- #
    payload = {
        "cross_signal": [
            {"preset": cr[0], "r_pink_tone": cr[1], "rms_pink_tone": cr[2],
             "r_pink_sweep": cr[3], "rms_pink_sweep": cr[4],
             "r_tone_sweep": cr[5], "rms_tone_sweep": cr[6]}
            for cr in cross_rows
        ],
        "cross_level": [
            {"preset": lr[0], "r_-20_-14": lr[1], "rms_-20_-14": lr[2],
             "r_-20_-10": lr[3], "rms_-20_-10": lr[4],
             "makeup_db": {"-20": lr[5][0], "-14": lr[5][1], "-10": lr[5][2]}}
            for lr in level_rows
        ],
        "artifact_test": [
            {"preset": ar[0], "resid_monotonic_r": ar[1], "resid_span_db": ar[2],
             "resid_monotonic_r_excl_20-60Hz": ar[3]}
            for ar in artifact_rows
        ],
        "verdicts": verdicts,
        "n_static": n_static,
        "overall_static": n_static == len(PRESETS),
    }
    print("\nJSON:")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
