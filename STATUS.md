# STATUS — read this first

_Last updated: 2026-06-17 · the single source of truth for "where are we."_
_New machine? Read `HANDOFF.md` first._

## Done

- [x] **Environment** — `.venv` with pinned stack (`requirements.txt`): numpy,
      scipy, matplotlib, pandas, soundfile, pyloudnorm. Python 3.13.
- [x] **8 test signals present & verified** in `source/test-signals/`
      (44.1 kHz · 16-bit · stereo · 60.000 s each). Do not regenerate.
- [x] **Measurement library** (`tools/audio_metrics.py`) — one canonical record
      per file: levels, true-peak, LUFS/LRA, per-band energy, slope, centroid,
      stereo, + signal-specific analyzers (tone ladder, click, dynamic, mid/side, sweep).
- [x] **Ground-truth registry** (`tools/signals.py`) — exact specs confirmed
      from the WAVs themselves (tone freqs, click period, dynamic levels, etc.).
- [x] **Validation pass** (`tools/validate_signals.py`) — **8/8 PASS, 0 fail, 0 warn**
      across 66 checks. Output: `measurements/validation/*.json`.
- [x] **Validation report** (`tools/report.py`) — `reports/validation/validation-report.html`
      (self-contained, charts embedded) + `validation-summary.md`.
- [x] **Fingerprint engine** (`tools/fingerprint.py`) — input→output deltas,
      per-preset aggregate, service `canonical.json`. **Self-test PASSES**:
      recovers a known injected +8 dB makeup + high-shelf brightening.
      (Fixed an NTFS `*.wav`/`*.WAV` glob double-count bug.)
- [x] **Real fingerprints + comparison** — **4 signals** (pink_−20, pink_−14,
      sine_sweep, tone_ladder) × **8 presets** = 32 masters measured.
      `tools/compare.py` → `reports/fingerprints/bandlab/comparison.html`.
      Canonical: `measurements/fingerprints/bandlab/canonical.json`.
- [x] **Onset alignment** added to tone/dynamic analyzers
      (`audio_metrics.content_onset`) — handles BandLab's 0.01–0.42 s lead-in.
      Validation still 8/8 PASS.

## Scope: 8 BandLab presets

`universal · clarity · oomph · tape · spatial · natural · warm · punch`
Full matrix = 8 signals × 8 presets = **64 masters**.

## Waiting on operator (Dan)

- [x] **4 signals × 8 presets done** (pink_−20, pink_−14, sine_sweep, tone_ladder)
      — fingerprinted + compared + pushed.
- [ ] **Remaining 4 signals × 8 presets = 32 masters** (Dan completing before the
      machine move): `pink_noise_minus10`, `click_track`, `dynamic_test_minus14`,
      `mid_side_test_minus20` through all 8 presets; drop in `competitors/bandlab/<preset>/`.
      - **LOCKED CAPTURE PROTOCOL (every upload):** input gain = 0.0 (decline the
        suggestion) · intensity = Normal. Stamped into every measurement from
        `competitors/bandlab/capture.json`.
      - Record the *suggested* input gain per signal before zeroing (free auto-gain
        data; 3 of 8 recorded — predictions for the rest in capture.json, esp.
        `click_track`, the peak-vs-loudness acid test).
      - Keep the source filename as a substring (e.g. `tone_ladder_minus20*.wav`).
      - **Suggested next batch:** the two other pink levels (−14, −10) → unlocks the
        level-dependence fingerprint; then `tone_ladder` (exact per-frequency gain).
      - If BandLab **rejects** any signal, record which — rejection is data.

## Next (agent, as signals arrive)

1. `tools/fingerprint.py --service bandlab` then `tools/compare.py --service bandlab`.
2. **Add onset alignment** to the tone/click/dynamic *output* analyzers — BandLab
   outputs run 0.01–0.42 s long (lead-in/tail), harmless for pink/broadband but it
   offsets segment-timed analyses. Detect content start before windowing.
3. `compare.py` already gates sections on signal presence — per-frequency gain,
   dynamics, stereo width, and limiter timing light up automatically as their
   signals land.

## Findings so far (BandLab)

- **Processing is level-dependent (adaptive) — confirmed.** Makeup gain differs by
  input level (oomph: +8.2 dB @ −20 vs +3.4 dB @ −14). So per-preset EQ curves are
  operating-point snapshots, not universal constants. pink_−10 adds the 3rd point.
- **Tone ladder cross-validates pink:** oomph reads +15 dB @ 40 Hz, independently
  confirming its +9.7 dB sub band. Two signals, one conclusion.
- **First tonal/loudness fingerprint (pink_noise_minus20, 8 presets):** loudest
  **punch** (−7.4 LUFS, +12 dB makeup, crest −6.6 = heaviest limiting, true-peak
  +1.1 dBTP); gentlest **warm** (−13.8 LUFS, +3 dB makeup, true-peak −3.6).
  Brightest **punch** (+2.18 dB/oct); only *darkening* preset **natural** (−0.26).
  Signature shapes: **oomph** +9.7 dB sub (20–60 Hz), **clarity** mid-scoop
  "smile," **spatial**/**tape** high-air lift, **universal** near-flat/safe.
  **5 of 8 exceed 0 dBTP** (inter-sample clipping): clarity, natural, spatial,
  universal, punch. Chart: `reports/fingerprints/bandlab/comparison.html`.
- **Auto input-gain is a peak normalizer to −4.5 dBFS — CONFIRMED on all 8 signals.**
  `suggested = −4.5 − input_peak_dbfs` (max error 0.05 dB). The `click_track` acid
  test passed: −4.1 = peak-target, not loudness-aware. Conditions for **headroom,
  not loudness**. Full per-signal table in `competitors/bandlab/capture.json`.
- **Intensity default = "Normal" = 50%** of a 0–100% range (dry→max). We run v1
  at this detent. Intensity sweep (0/50/100) is Phase 2 — and intensity-0 doubles
  as a rig self-check (near-zero delta would validate the measurement; residual
  loudness/limiting would expose the "always-on" part of the chain).

## Decisions / notes for future sessions

- **All audio is now committed** (competitor masters included) so the full dataset
  travels with the repo — overrides the original spec's gitignore-competitors rule.
  Migrate WAVs to Git LFS if the corpus grows large. See `HANDOFF.md` §8.
- `source/original-references/` (~344 MB real-music masters) was **removed by the
  operator**; the old gitignore rule is gone.
- Outputs are assumed **time-aligned** with inputs (mastering doesn't
  time-stretch). `fingerprint.py` warns if duration differs by >0.1 s.
- The 8 test-signal WAVs (~80 MB) **are** committed — they're the fixed constants.
- EQ "shape" = band energy with makeup gain removed; that's the tonal
  fingerprint independent of loudness. Raw band deltas are also stored.

## Future work (explicitly later)

- Additional services (LANDR, eMastered, CloudBounce) — same methodology, new
  dir under `competitors/`. Registry/engine already service-agnostic.
- Adaptive profiling with diverse real music to isolate track-specific behavior.
