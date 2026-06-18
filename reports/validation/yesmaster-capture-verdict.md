# YES Master Capture — Verification Verdict

_Settles the question: "Were Codex's YES Master captures done correctly — in particular,
was the intensity really 0.5 (matching BandLab's 'Normal'), and do the committed numbers
honestly reflect the audio?"_

**Verdict: YES on all counts. The YES Master dataset is trustworthy and directly
comparable to the BandLab dataset.** Verified three independent ways that cannot all be
wrong at once.

## What was checked

### 1. Measurement fidelity — do the committed numbers match the audio?
`tools/verify_yesmaster_independent.py` re-derives output LUFS, true-peak, stereo
correlation change, and per-band raw deltas **straight from the committed WAVs with
fresh DSP** (own Welch PSD, resample-poly true-peak, corrcoef stereo) — it does NOT
import the project's measurement code. Across spatial / oomph / custom / punch /
universal, every load-bearing number matched the committed fingerprints to **≤0.001 dB**.
→ The measurement is faithful. (The "stereo axis is dead, even on `spatial`" finding is
real, not a meter artifact: `spatial` correlation change = −0.006.)

### 2. Capture settings — was intensity 0.5 / input gain 0 on every render?
- **Metadata:** `tools/verify_yesmaster_capture_audit.py` confirms all **144 renders**
  (72 per set × 2 sets) recorded `effective_adaptive_strength = 0.5` and
  `input_gain_db = 0.0`, full 9-preset × 8-signal coverage, zero stragglers.
- **Source code:** the render harness
  (`yes-master/test-output/yesmaster-fingerprint-runner/src/main.rs`,
  `fingerprint_settings`) **hardcodes** `settings.intensity = 0.5; input_gain_db = 0.0;
  output_gain_db = 0.0; volume_match = false;` and passes that exact struct to
  `mastering_render_to_path`. There is no path where 0.5 is recorded but a different
  value is applied. → The setting is the application.

### 3. Reproduction — does a fresh render off the real engine land on the same numbers?
A new render of all 9 presets (`competitors/yesmaster-recheck/`, signals pink_−20 +
mid/side, per-preset loudness-parity targets) was produced by the **actual YES Master
engine** and measured independently (`tools/verify_recheck_reproduction.py`). It
reproduces the originally committed loudness-parity fingerprints to **≤0.001 dB on every
metric, every preset**. → The capture is deterministic and the recorded settings really
were applied.

### 4. Intensity knob is wired
Sweeping `universal` / pink_−20 across intensity 0.0 → 0.5 → 1.0 shifts the spectrum by
~0.6 dB (band energy) while loudness stays pinned by the target. The knob moves the
sound, so 0.5 is a genuine intermediate setting — not a stuck/ignored default. (Effect is
modest here because pink noise has no transients for the dynamics stage to act on and
`universal` is the gentlest preset; expect a larger effect on punchy presets with real
music.)

## Bottom line
YES Master was captured with the same neutral protocol as BandLab (input gain 0,
intensity 0.5), the measurements are faithful, and the dataset reproduces exactly off the
live engine. Conclusions drawn from comparing YES Master to BandLab rest on verified
ground.
