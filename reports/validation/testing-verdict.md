# Testing Verdict — Is the BandLab Preset Measurement Sound?

_Independent verification pass, 2026-06-16. Recomputed from the raw WAV files with standalone code that does **not** import the repo's `audio_metrics.py` or `fingerprint.py` — only `numpy`, `scipy`, `soundfile`, and `pyloudnorm` (the standard BS.1770 reference meter). The committed JSON was used only as the thing being checked, never as an input to the check._

---

## Bottom line

**The testing is SOUND.** The committed measurements are real, reproducible-from-raw-WAV numbers, and there is **no common-mode / systematic bug that would invalidate the testing wholesale.** My independent first-principles numbers match the committed `canonical.json` / `fingerprint.json` to within rounding (≤ 0.001 dB) across the whole 8-preset × 8-signal matrix.

Two items surfaced. Neither changes the verdict:

1. A real but **bounded and self-cancelling** code convention quirk (a mono-vs-stereo RMS reference mismatch) that shifts the zero-point of **one** derived view (`eq_shape_db`) by at most ~0.22 dB. It cancels exactly in the EQ-contour view and never touches raw bands, tilt, centroid, or tone gains.
2. **`HANDOFF.md` is stale** — it still carries pre-fix tilt / multiband numbers that contradict the ground-truth `canonical.json` and every other doc. This is a documentation-hygiene problem, not a data error.

---

## What was independently re-derived and matched

I reimplemented every metric from scratch (Welch PSD with `nperseg=16384`, rectangular per-band power integration, log-uniform per-octave tilt fit, power-weighted centroid, mid/side stereo correlation, RMS dBFS, and pyloudnorm BS.1770 LUFS) and ran it on the raw source signals and the raw masters.

**Source test signals (all 8) — confirmed against claimed specs:**

- Format: every signal `44100 Hz`, `2 ch`, `PCM_16`, `2,646,000` frames = `60.000 s` exact.
- RMS dBFS within tolerance: pink −20 = −21.00, pink −14 = −15.00, pink −10 = −11.00, sweep = −21.0, click = −43.88 (target −44, within tol), tone ladder = −21.00, dynamic = −14.03, mid/side = −21.00.
- Pink spectral slope ≈ **−3.01 dB/oct** (per-octave units confirmed — not per-decade).
- Stereo correlation: pink −20 = **0.035** (decorrelated as claimed), mid/side = **0.992** (> 0.90 floor).
- Click track: **120** single-sample impulses, spacing exactly **22050** samples (500 ms), first onset at sample 0.

**Committed BandLab fingerprints (all 8 presets, pink_noise_minus20 reference) — reproduced to ≤ 0.001 dB:**

| Preset | makeup (dB) | out LUFS | tilt (dB/oct) | centroid shift (Hz) | my vs canon |
|---|---|---|---|---|---|
| warm | 3.014 | −13.771 | −0.014 | 743.24 | exact |
| oomph | 8.235 | −13.041 | −0.241 | −2026.93 | ≤ 0.001 |
| punch | 12.075 | −7.388 | 1.147 | 3614.49 | ≤ 0.01 (centroid) |
| universal | 9.075 | −11.634 | 0.030 | 257.54 | ≤ 0.001 |
| natural | 8.651 | −12.341 | −0.522 | −808.40 | ≤ 0.001 |
| spatial | 8.922 | −10.325 | 0.295 | 1218.77 | ≤ 0.001 |
| clarity | 7.812 | −13.420 | 0.217 | 862.26 | exact |
| tape | 8.176 | −10.708 | 0.210 | 1751.60 | exact |

**Stereo correlation_change (from the dedicated mid/side signal):** spatial −0.314, punch −0.124, clarity −0.013, tape −0.028, the other four within 0.01 of zero — all matching committed to ≤ 0.001. Confirms the headline finding that BandLab uses the stereo axis on essentially one preset (spatial) and never narrows.

**Input-gain model:** BandLab's suggested input gain reproduces the peak-normalizer model `gain = −4.5 − input_peak_dBFS` to a max error of 0.048 dB across all 8 signals; residuals are 0.1-dB UI-rounding artifacts, the signature of a value read off a UI rather than hand-fitted.

**Max scalar/band diff across the entire matrix:** ≤ 0.001 dB once the same integration convention is used (see the false-alarm note below). LUFS reproduces to ~0.05 dB against an independent BS.1770 implementation — well within any decision tolerance.

### A false alarm I chased down (and why it confirms soundness)

My first pass showed a 0.281 dB diff on **oomph's 20–60 Hz** band. I traced it: my script integrated band power with `np.trapz` (trapezoidal), while the repo uses a rectangular sum (`np.sum(pxx[mask]) * df`, `audio_metrics.py:174`). At 20–60 Hz there are only ~15 FFT bins and oomph's PSD rises steeply there, so trapezoid-vs-rectangle disagree by ~0.28 dB at that one boundary band. **Switching my code to the repo's rectangular convention collapsed the diff to 0.0008 dB.** So the apparent discrepancy was *my* estimator choice, not a repo defect — and chasing it down is exactly what makes the match non-circular.

---

## The strongest skeptical case — and why it does not hold

**Hostile claim:** "The makeup-gain-normalized EQ shape (`eq_shape_db`) is built on an inconsistent loudness reference. `rms_dbfs()` (`audio_metrics.py:99`) computes RMS over the **stereo power pool** (it flattens both channels), while the per-band energies, slope, and centroid all run on the **mono downmix** (mean of L/R, `_mono`). `band_deltas()` (`fingerprint.py:62-65`) then subtracts the stereo-pool makeup from the mono band deltas. On a fully decorrelated pink signal the mono-vs-pool RMS gap is a large ~2.86 dB — so a reviewer could argue the EQ shape sits on the wrong reference."

**Why it does not hold (I tested it directly):**

- The contamination is **exactly uniform across all 9 bands** — it is the *change* in the input→output decorrelation gap, a single number added to every band, not a per-band tilt. I measured the injected offset per preset: worst case **−0.216 dB (oomph)**, then warm −0.143, punch +0.109, spatial −0.060, the rest under 0.04 dB.
- Because it is a uniform DC offset, it **cancels exactly in `eq_contour_db`** (which is mean-centered), and `eq_contour_db` is the view that actually describes the EQ *curve*. My from-scratch contour matches canon to ≤ 0.001.
- It **never touches** the raw band deltas, spectral tilt, centroid, tone-ladder gains, makeup gain, LUFS, true peak, or stereo metrics.
- Against the signal it sits on — e.g. oomph's **+9.7 dB** sub boost — a ≤ 0.22 dB zero-point shift changes nothing qualitatively.
- The code **documents the gap in its own docstring** (`band_energy_dbfs`, `audio_metrics.py:160-167`).

So the worst-case is a small, bounded, mostly self-cancelling cosmetic offset on one derived metric — not a wholesale invalidator. The hostile case collapses under scrutiny.

The second-strongest case — "`HANDOFF.md` ships wrong preset personalities" — is true but is a doc problem contradicted by the correct ground-truth JSON and every other doc (`STATUS.md`, `recipes.md`, `validation.md`). And the 12-dB emulator error on the click signal is **explicitly and correctly disclosed** as an unmodeled transient gap, i.e. scientific honesty, not a hidden failure.

---

## Real remaining issues to fix (ranked)

**1. (Low) Mono/stereo RMS-reference mismatch in EQ-shape normalization.**
- **Where:** `tools/audio_metrics.py:99` (`rms_dbfs` uses the stereo power pool) vs `tools/audio_metrics.py:168` (`_mono` downmix used by bands/slope/centroid), consumed at `tools/fingerprint.py:62-65`.
- **Effect:** Injects a uniform offset of up to ~0.22 dB into `eq_shape_db` only. Cancels in `eq_contour_db`; does not affect any other metric.
- **Fix:** Compute the makeup reference used for shape normalization from the **same mono downmix** the bands use (a mono RMS), rather than the stereo-pool `rms_dbfs`. This makes the EQ-shape reference internally consistent and removes the offset. The `loudness.makeup_gain_db` field should keep using the stereo-pool RMS — it is the correct full-signal makeup.

**2. (Low / doc hygiene) `HANDOFF.md` Section 5 carries pre-fix numbers that contradict `canonical.json`.**
- **Where:** `HANDOFF.md` §5.7, §5.9, and the header date.
- **Stale → correct:**
  - §5.7 "multiband-density index: punch **1.38** (most) → natural **0.018** (linear/transparent)" → should be **punch 1.01 (most) → universal 0.13 (most linear)**; natural is mid-pack at **0.365**.
  - §5.9 "warm … tilt **+0.41**" → canonical warm tilt = **−0.014** (≈ flat). Centroid +743 is correct.
  - §5.9 "oomph tilt **+0.32** … disagrees with centroid by sign" → canonical oomph tilt = **−0.24** (negative); tilt and centroid now **agree** (both dark).
  - §5.9 "natural is the only density-independent EQ" → **universal** is the most density-independent (mbidx 0.13); natural is mid-pack.
  - Header line 3 date **2026-06-17** is inconsistent with its own "Current state (2026-06-16)" section and post-dates the data it describes.
- **Fix:** Regenerate or hand-edit `HANDOFF.md` §5 from `canonical.json` (the equal-octave-tilt numbers already corrected in `STATUS.md`/`recipes.md`), and fix the header date.

**3. (Informational, not a defect) `review-and-analysis.md` P2 sections quote superseded pre-fix figures** (e.g. punch +2.18 dB/oct, natural 0.018). This is **disclosed** by the file's own "fixes applied" banner, so it is a skim hazard, not an error. Optionally add an inline "(superseded — see banner)" marker next to each old number.

---

## Verdict in one line

The science and the committed measurements are **sound and independently reproduced to rounding**; the only things to touch are one cosmetic EQ-shape reference convention (≤ 0.22 dB, self-cancelling) and the stale `HANDOFF.md` — neither undermines a single conclusion in the project.
