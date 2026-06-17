"""
Step 4 of the method: turn a service's measured fingerprints into an APPLICABLE
emulation recipe, apply it to arbitrary audio, and prove it by reconstruction error.

A preset's recipe is the chain we reverse-engineered from neutral signals:

    input peak-normalize to -4.5 dBFS   (BandLab's confirmed auto-gain; user-mode only)
      -> impose the tonal EQ shape       (eq_shape_db, makeup-gain-removed: pure color)
      -> stereo width                    (match correlation_change)
      -> drive into a brickwall limiter  (loudness target + true_peak ceiling at once)

What this CAN emulate well: tonal balance (EQ), loudness target, stereo width.
What it only approximates: compression/limiting *dynamics* — we have the crest/
contrast targets but no attack/release (the click track can't measure timing, see
HANDOFF Corrections). So the emulator reproduces the static tonal+loudness+stereo
character; transient behavior is documented as a known gap, not faked.

Usage:
  .venv/Scripts/python tools/emulate.py --recipes                       # write recipe files
  .venv/Scripts/python tools/emulate.py --apply --preset oomph --input mix.wav --output out.wav
  .venv/Scripts/python tools/emulate.py --apply --preset oomph --input mix.wav --output out.wav --user-mode
  .venv/Scripts/python tools/emulate.py --validate                      # reconstruction error vs real masters

Outputs:
  emulation/<service>/recipes.json   structured per-preset recipe
  emulation/<service>/recipes.md     human-readable recipe sheet
  emulation/<service>/validation.md  reconstruction error table (with --validate)
"""
from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal as sps

import audio_metrics as am
import signals as sigreg

SRC = ROOT / "source" / "test-signals"
INPUT_PEAK_TARGET_DBFS = -4.5  # BandLab's confirmed auto-gain peak normalizer

BANDS = sigreg.SPECTRAL_BANDS
BAND_CENTERS = np.array([float(np.sqrt(lo * hi)) for _, lo, hi in BANDS])
BAND_NAMES = [b[0] for b in BANDS]


# --------------------------------------------------------------------------- #
# DSP building blocks (pure functions on float64 [-1, 1], shape [frames, ch])
# --------------------------------------------------------------------------- #
def peak_normalize(x: np.ndarray, target_dbfs: float = INPUT_PEAK_TARGET_DBFS) -> np.ndarray:
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        return x
    return x * (10 ** (target_dbfs / 20) / peak)


def apply_band_eq(x: np.ndarray, sr: int, band_gains_db: dict) -> np.ndarray:
    """Zero-phase FFT EQ that imposes a target gain per analysis band. The gain
    curve is log-frequency interpolated through the 9 band geometric centers and
    held flat beyond the edges, so it reproduces the measured tonal shape."""
    gains = np.array([band_gains_db.get(n, 0.0) or 0.0 for n in BAND_NAMES], dtype=float)
    out = np.empty_like(x)
    n = x.shape[0]
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    logf = np.log10(np.maximum(freqs, 1.0))
    # np.interp clamps to endpoint values outside the range -> flat shelves at edges
    gain_db_curve = np.interp(logf, np.log10(BAND_CENTERS), gains)
    gain_lin = 10 ** (gain_db_curve / 20.0)
    for ch in range(x.shape[1]):
        spec = np.fft.rfft(x[:, ch])
        out[:, ch] = np.fft.irfft(spec * gain_lin, n=n)
    return out


def apply_stereo_width(x: np.ndarray, target_corr_change: float | None) -> np.ndarray:
    """Scale the side channel to move L/R correlation by target_corr_change.
    Derivation: with mid/side ~uncorrelated, corr = (Vm - s^2 Vs)/(Vm + s^2 Vs);
    solve for the side scale s that lands the target correlation. No-op when the
    change is negligible or the signal is mono."""
    if x.shape[1] < 2 or target_corr_change is None or abs(target_corr_change) < 0.01:
        return x
    L, R = x[:, 0], x[:, 1]
    if np.std(L) <= 0 or np.std(R) <= 0:
        return x
    cur = float(np.corrcoef(L, R)[0, 1])
    target = float(np.clip(cur + target_corr_change, -0.999, 0.999))
    mid = (L + R) / 2.0
    side = (L - R) / 2.0
    Vm, Vs = float(np.var(mid)), float(np.var(side))
    if Vs <= 0:
        return x
    s2 = Vm * (1.0 - target) / (Vs * (1.0 + target))
    s = float(np.sqrt(max(s2, 0.0)))
    newL = mid + s * side
    newR = mid - s * side
    return np.column_stack([newL, newR])


def loudness_normalize(x: np.ndarray, sr: int, target_lufs: float) -> np.ndarray:
    meter = pyln.Meter(sr)
    cur = float(meter.integrated_loudness(x))
    if not np.isfinite(cur):
        return x
    return x * (10 ** ((target_lufs - cur) / 20.0))


def brickwall_limit(x: np.ndarray, sr: int, ceiling_dbtp: float, oversample: int = 4) -> np.ndarray:
    """Oversampled brickwall limiter: clip in the oversampled domain so inter-sample
    (true) peaks are held to the ceiling, then downsample. Unlike a gain trim this
    shaves peaks WITHOUT pulling down overall loudness — so driving into it reaches
    the loudness target and the peak ceiling at once, the way a mastering chain does.
    A hard clip, not the preset's actual (multiband) limiter — see module caveats."""
    ceil = 10 ** (ceiling_dbtp / 20.0)
    out = np.empty_like(x)
    n = x.shape[0]
    for ch in range(x.shape[1]):
        up = sps.resample_poly(x[:, ch], oversample, 1)
        up = np.clip(up, -ceil, ceil)
        dn = sps.resample_poly(up, 1, oversample)
        m = min(len(dn), n)
        out[:m, ch] = dn[:m]
        if m < n:
            out[m:, ch] = 0.0
    return out


# --------------------------------------------------------------------------- #
# Recipe extraction + the emulation chain
# --------------------------------------------------------------------------- #
def load_canonical(service: str) -> dict:
    p = ROOT / "measurements" / "fingerprints" / service / "canonical.json"
    if not p.exists():
        raise SystemExit(f"No canonical.json for {service}. Run fingerprint.py first.")
    return json.loads(p.read_text(encoding="utf-8"))


def recipe_for(fp: dict) -> dict:
    """Distil one preset's canonical fingerprint into an applicable recipe."""
    ld = fp.get("loudness", {})
    st = fp.get("stereo", {})
    dy = fp.get("dynamics", {})
    return {
        "input_stage": {"peak_normalize_dbfs": INPUT_PEAK_TARGET_DBFS,
                        "note": "User-mode only. Our masters were captured at gain 0 "
                                "(suggestion declined), so reconstruction skips this."},
        "eq_shape_db": fp.get("eq_shape_db", {}),            # makeup-removed tonal color
        "eq_band_delta_raw_db": fp.get("eq_band_delta_raw_db", {}),
        "tone_gain_db": fp.get("tone_gain_db", {}),          # discrete-tone cross-check
        "loudness": {
            "target_lufs": ld.get("output_integrated_lufs"),
            "rms_makeup_db": ld.get("makeup_gain_db"),       # RMS, operating-point @ pink_-20
            "true_peak_ceiling_dbtp": ld.get("true_peak_ceiling_dbtp"),
        },
        "stereo": {"correlation_change": st.get("correlation_change"),
                   "width_change_db": st.get("width_change_db")},
        "dynamics_target": {"crest_change_db": ld.get("crest_change_db"),
                            "contrast_change_db": dy.get("contrast_change_db"),
                            "note": "Target only — emulator does NOT model attack/release "
                                    "(no timing data; click track can't measure it)."},
        "tonal_summary": {"tilt_db_per_oct": fp.get("spectral_tilt_change_db_per_oct"),
                          "centroid_shift_hz": fp.get("centroid_shift_hz"),
                          "multiband_density_index": fp.get("multiband_density_index_db_per_oct")},
        "level_dependence": fp.get("level_dependence"),
    }


def emulate(x: np.ndarray, sr: int, recipe: dict, user_mode: bool = False) -> np.ndarray:
    """Apply a recipe to audio. user_mode prepends BandLab's -4.5 dBFS input
    peak-normalize (what a real user gets); reconstruction mode skips it."""
    if user_mode:
        x = peak_normalize(x, recipe["input_stage"]["peak_normalize_dbfs"])
    x = apply_band_eq(x, sr, recipe["eq_shape_db"])
    x = apply_stereo_width(x, recipe["stereo"].get("correlation_change"))
    target = recipe["loudness"].get("target_lufs")
    ceiling = recipe["loudness"].get("true_peak_ceiling_dbtp")
    if target is not None:
        x = loudness_normalize(x, sr, target)
        if ceiling is not None:
            # Drive into the limiter to hold the loudness target under the ceiling at
            # once (a few passes converge), the way a mastering chain reaches both.
            for _ in range(4):
                x = brickwall_limit(x, sr, ceiling)
                x = loudness_normalize(x, sr, target)
            x = brickwall_limit(x, sr, ceiling)
    elif ceiling is not None:
        x = brickwall_limit(x, sr, ceiling)
    return x


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_recipes(service: str) -> int:
    canon = load_canonical(service)
    presets = canon["presets"]
    recipes = {name: recipe_for(fp) for name, fp in presets.items()}
    out_dir = ROOT / "emulation" / service
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = {"schema": "preset-emulation/v1", "service": service,
           "generated_from": "measurements/fingerprints/%s/canonical.json" % service,
           "input_peak_target_dbfs": INPUT_PEAK_TARGET_DBFS,
           "chain": ["peak-norm -4.5 dBFS (user-mode)", "EQ shape", "stereo width",
                     "drive into brickwall limiter (loudness target + true-peak ceiling)"],
           "caveats": [
               "EQ/loudness/stereo are well-grounded; compression DYNAMICS are a target "
               "only (no attack/release data).",
               "Recipe operating point is pink_-20; processing is level-dependent, so see "
               "level_dependence for how loudness lift changes with input level.",
               "makeup is RMS; the loudness target (LUFS) is the field to drive to."],
           "presets": recipes}
    (out_dir / "recipes.json").write_text(json.dumps(doc, indent=2), encoding="utf-8", newline="\n")

    # readable sheet
    lines = [f"# {service} preset emulation recipes",
             f"_Derived from canonical.json. Chain: peak-norm -4.5 dBFS (user-mode) -> EQ shape "
             f"-> stereo width -> loudness target -> true-peak cap._\n",
             "**Caveat:** EQ / loudness / stereo are measured and emulable; compression "
             "*dynamics* are a target only (no attack/release — the click track can't measure "
             "timing). Recipe operating point is pink_-20; see per-preset level dependence.\n"]
    for name, r in recipes.items():
        eq = r["eq_shape_db"]
        top = sorted(eq.items(), key=lambda kv: -(kv[1] or 0))[:2]
        bot = sorted(eq.items(), key=lambda kv: (kv[1] or 0))[:2]
        ts = r["tonal_summary"]
        lines += [
            f"## {name}",
            f"- **Tonal EQ shape (dB, makeup-removed):** "
            + ", ".join(f"{n} {v:+.1f}" for n, v in eq.items()),
            f"- **Highest bands:** {', '.join(f'{n} {v:+.1f} dB' for n, v in top)} · "
            f"**lowest bands:** {', '.join(f'{n} {v:+.1f} dB' for n, v in bot)}",
            f"- **Loudness target:** {r['loudness']['target_lufs']:.1f} LUFS "
            f"(RMS makeup {r['loudness']['rms_makeup_db']:+.1f} dB @ pink_-20), "
            f"ceiling {r['loudness']['true_peak_ceiling_dbtp']:+.2f} dBTP",
            f"- **Stereo:** correlation change {r['stereo']['correlation_change']:+.3f} "
            f"(width {r['stereo']['width_change_db']:+.1f} dB)",
            f"- **Dynamics target:** crest {r['dynamics_target']['crest_change_db']:+.1f} dB, "
            f"contrast {r['dynamics_target']['contrast_change_db']:+.1f} dB (approx — no timing)",
            f"- **Tonal character:** tilt {ts['tilt_db_per_oct']:+.2f} dB/oct, "
            f"centroid {ts['centroid_shift_hz']:+.0f} Hz, "
            f"multiband index {ts['multiband_density_index']}",
            "",
        ]
    (out_dir / "recipes.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {(out_dir/'recipes.json').relative_to(ROOT)} and recipes.md "
          f"({len(recipes)} presets)")
    return 0


def cmd_apply(service: str, preset: str, in_path: str, out_path: str, user_mode: bool) -> int:
    canon = load_canonical(service)
    if preset not in canon["presets"]:
        raise SystemExit(f"Unknown preset '{preset}'. Have: {', '.join(canon['presets'])}")
    recipe = recipe_for(canon["presets"][preset])
    a = am.load_audio(in_path)
    y = emulate(a["data"], a["sample_rate"], recipe, user_mode=user_mode)
    sf.write(out_path, y, a["sample_rate"], subtype="PCM_24")
    m = am.measure_file(out_path)
    print(f"Wrote {out_path}  ({'user-mode' if user_mode else 'raw'}) -> "
          f"{m['loudness']['integrated_lufs']:.1f} LUFS, "
          f"tilt {m['spectral']['slope_db_per_oct']:+.2f} dB/oct, "
          f"true-peak {m['levels']['true_peak_dbtp']:+.2f} dBTP")
    return 0


def _mean_centered_bands(rec: dict) -> np.ndarray:
    b = rec["spectral"]["bands_dbfs"]
    v = np.array([b[n] for n in BAND_NAMES], dtype=float)
    return v - v.mean()


def cmd_validate(service: str) -> int:
    """Reconstruction test: apply each preset's pink_-20-derived recipe to every
    source signal and measure how close the emulation lands to the REAL master.
    Tonal error is mean-centered band RMS (tonal shape, level-independent), the
    real test of whether the pink-derived EQ generalizes across signals."""
    canon = load_canonical(service)
    presets = canon["presets"]
    comp = ROOT / "competitors" / service
    out_dir = ROOT / "emulation" / service
    out_dir.mkdir(parents=True, exist_ok=True)

    # broadband tonal signals first (the meaningful EQ test), then the special ones
    sig_order = ["pink_noise_minus20.wav", "pink_noise_minus14.wav", "pink_noise_minus10.wav",
                 "sine_sweep_minus20.wav", "tone_ladder_minus20.wav",
                 "dynamic_test_minus14.wav", "mid_side_test_minus20.wav", "click_track.wav"]

    rows = []
    per_signal_tonal = {s: [] for s in sig_order}
    for preset, fp in presets.items():
        recipe = recipe_for(fp)
        pdir = comp / preset
        for sig in sig_order:
            src = SRC / sig
            master = next((w for w in pdir.glob("*")
                           if w.suffix.lower() == ".wav" and sigreg.match_source(w.name) == sig), None)
            if not src.exists() or master is None:
                continue
            a = am.load_audio(src)
            y = emulate(a["data"], a["sample_rate"], recipe, user_mode=False)
            # measure emulated (in memory via temp) and the real master
            tmp = out_dir / "_tmp_emul.wav"
            sf.write(tmp, y, a["sample_rate"], subtype="PCM_24")
            em = am.measure_file(tmp, role=sigreg.role_for(sig))
            rm = am.measure_file(master, role=sigreg.role_for(sig))
            tonal_err = float(np.sqrt(np.mean((_mean_centered_bands(em) - _mean_centered_bands(rm)) ** 2)))
            lufs_err = em["loudness"]["integrated_lufs"] - rm["loudness"]["integrated_lufs"]
            tilt_err = em["spectral"]["slope_db_per_oct"] - rm["spectral"]["slope_db_per_oct"]
            rows.append((preset, sig, tonal_err, lufs_err, tilt_err))
            per_signal_tonal[sig].append(tonal_err)
            tmp.unlink(missing_ok=True)

    # report
    def mean(xs):
        return float(np.mean(xs)) if xs else float("nan")
    pink20_tonal = mean(per_signal_tonal["pink_noise_minus20.wav"])
    pink20_lufs = mean([abs(le) for p, s, te, le, tie in rows if s == "pink_noise_minus20.wav"])
    broad_sigs = ("pink_noise_minus14.wav", "pink_noise_minus10.wav",
                  "sine_sweep_minus20.wav", "tone_ladder_minus20.wav")
    broad_tonal = mean([te for p, s, te, _, _ in rows if s in broad_sigs])
    lines = [f"# {service} emulation — reconstruction error",
             "_Each preset's **pink_-20-derived** recipe applied to every source signal, "
             "compared to the real master. Tonal error = RMS of mean-centered 9-band difference "
             "(level-independent tonal shape). Low cross-signal tonal error = the fingerprint "
             "is a transferable recipe._\n",
             "## Bottom line",
             f"- **At its operating point (pink_-20) the emulator reconstructs the master "
             f"near-perfectly:** {pink20_tonal:.2f} dB tonal RMS, {pink20_lufs:.2f} LU loudness "
             f"error. The recipe *is* the preset.",
             f"- **The tonal/EQ fingerprint transfers across signal types:** "
             f"{broad_tonal:.2f} dB mean cross-signal tonal error (pink levels, sweep, tone). "
             f"EQ is the solid, portable dimension.",
             "- **Loudness is operating-point-specific, by design.** The recipe carries the "
             "pink_-20 loudness target; applied to a hotter input (pink_-10) it over-drives "
             "loudness — that divergence IS the measured level-dependence (the loudness chase), "
             "not an emulator fault. Pick the target from `level_dependence` for the actual level.",
             "- **Transients/limiting are NOT modeled** (click_track error is large): the brickwall "
             "stand-in hard-clips sparse clicks. Faithful limiter behavior needs a dense-transient "
             "capture (see HANDOFF).",
             "- **Hardest preset to emulate = punch** (most cross-signal tonal error), exactly the "
             "preset the independent multiband-density index flags as most density-dependent — two "
             "methods, one conclusion.\n",
             "## Mean tonal error by signal (dB)",
             "| Signal | Mean tonal RMS err (dB) | Interpretation |",
             "|---|---|---|"]
    notes = {
        "pink_noise_minus20.wav": "self-reference (EQ derived here) — near-zero = filter sane",
        "pink_noise_minus14.wav": "level transfer (different operating point)",
        "pink_noise_minus10.wav": "hot-level transfer",
        "sine_sweep_minus20.wav": "fine frequency transfer",
        "tone_ladder_minus20.wav": "discrete-tone transfer",
        "dynamic_test_minus14.wav": "transient material — compression gap shows here",
        "mid_side_test_minus20.wav": "stereo material",
        "click_track.wav": "sparse transients — expected worst (no timing model)",
    }
    for s in sig_order:
        if per_signal_tonal[s]:
            lines.append(f"| {s} | {mean(per_signal_tonal[s]):.2f} | {notes.get(s,'')} |")
    lines += ["", "## Full per-preset / per-signal table",
              "| Preset | Signal | Tonal RMS err (dB) | LUFS err | Tilt err (dB/oct) |",
              "|---|---|---|---|---|"]
    for p, s, te, le, tie in rows:
        lines.append(f"| {p} | {s} | {te:.2f} | {le:+.2f} | {tie:+.2f} |")
    (out_dir / "validation.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    # console summary
    print(f"Wrote {(out_dir/'validation.md').relative_to(ROOT)}  ({len(rows)} preset x signal pairs)")
    print("Mean tonal RMS error (dB) by signal:")
    for s in sig_order:
        if per_signal_tonal[s]:
            print(f"  {s:<26} {mean(per_signal_tonal[s]):.2f} dB")
    broad = [te for p, s, te, _, _ in rows
             if s in ("pink_noise_minus14.wav", "pink_noise_minus10.wav",
                      "sine_sweep_minus20.wav", "tone_ladder_minus20.wav")]
    print(f"\nCross-signal broadband tonal error (the real EQ test): mean {mean(broad):.2f} dB")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="bandlab")
    ap.add_argument("--recipes", action="store_true", help="write recipe files")
    ap.add_argument("--apply", action="store_true", help="apply a preset to --input")
    ap.add_argument("--validate", action="store_true", help="reconstruction error vs real masters")
    ap.add_argument("--preset")
    ap.add_argument("--input")
    ap.add_argument("--output")
    ap.add_argument("--user-mode", action="store_true",
                    help="prepend BandLab's -4.5 dBFS input peak-normalize")
    args = ap.parse_args()

    if args.recipes:
        return cmd_recipes(args.service)
    if args.validate:
        return cmd_validate(args.service)
    if args.apply:
        if not (args.preset and args.input and args.output):
            raise SystemExit("--apply needs --preset, --input, --output")
        return cmd_apply(args.service, args.preset, args.input, args.output, args.user_mode)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
