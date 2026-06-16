# STATUS — read this first

_Last updated: 2026-06-16 · the single source of truth for "where are we."_

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

## Waiting on operator (Dan)

- [ ] **BandLab masters.** Upload each of the 8 signals through the 4 BandLab
      presets (**Universal, Clarity, Oomph, Tape**) = 32 files. Download WAVs and
      drop them in `competitors/bandlab/<preset>/`.
      - **LOCKED CAPTURE PROTOCOL (identical on every upload):**
        **input gain = 0.0** (manual override of the suggestion) ·
        **intensity = Normal (50%)** (the default detent). See
        `competitors/bandlab/capture.json` — `fingerprint.py` reads it and stamps
        every measurement with this provenance.
      - **Also record the *suggested* input gain per signal** (the value BandLab
        proposes before you zero it). It's a free readout of their input
        conditioning. 3 of 8 recorded; predictions for the rest in capture.json.
      - Keep the source filename as a substring so auto-matching works
        (e.g. `pink_noise_minus20*.wav`). Unmatched files are reported, not guessed.
      - **Priority order if batching:** start with `pink_noise_minus20.wav`
        (primary tonal reference) through all 4 presets — that alone yields a
        first comparative EQ fingerprint.
      - If BandLab **rejects** any signal, record which one(s) — rejection is data.

## Next (agent, once data lands)

1. Run `tools/fingerprint.py --service bandlab`. Verify per-preset
   `fingerprint.json` + `canonical.json` are written.
2. **Build the fingerprint HTML report** (not yet built — deferred until real
   output shapes are known). Reuse `report.py` chart helpers: input-vs-output
   spectrum overlays, per-preset EQ-curve charts, a 4-preset comparison matrix.
3. Sanity-check deltas against expectation (BandLab presets are loud; expect
   large +makeup gain and a true-peak ceiling near −1 to −0.1 dBTP).

## Findings so far (BandLab)

- **Auto input-gain is a peak normalizer to ≈ −4.5 dBFS.** BandLab's "suggested
  input gain" follows `suggested = −4.5 − input_peak_dbfs`. Confirmed on 3 pink
  levels (−20→+2.5, −14→−3.9, −10→−4.5), all landing within 0.05 dB of −4.5 dBFS
  peak. It conditions for **headroom, not loudness**. To verify: `click_track`
  (sparse, peak −0.45) should suggest ≈ −4.1 if peak-targeted; a big positive
  boost would mean loudness-aware gating instead. Full model + predictions in
  `competitors/bandlab/capture.json`.
- **Intensity default = "Normal" = 50%** of a 0–100% range (dry→max). We run v1
  at this detent. Intensity sweep (0/50/100) is Phase 2 — and intensity-0 doubles
  as a rig self-check (near-zero delta would validate the measurement; residual
  loudness/limiting would expose the "always-on" part of the chain).

## Decisions / notes for future sessions

- `source/original-references/` (~344 MB real-music masters) is **gitignored** —
  not part of the locked spec; it's future adaptive-profiling material. Use Git
  LFS if you want it versioned.
- Outputs are assumed **time-aligned** with inputs (mastering doesn't
  time-stretch). `fingerprint.py` warns if duration differs by >0.1 s.
- The 8 test-signal WAVs (~80 MB) **are** committed — they're the fixed constants.
- EQ "shape" = band energy with makeup gain removed; that's the tonal
  fingerprint independent of loudness. Raw band deltas are also stored.

## Future work (explicitly later)

- Additional services (LANDR, eMastered, CloudBounce) — same methodology, new
  dir under `competitors/`. Registry/engine already service-agnostic.
- Adaptive profiling with diverse real music to isolate track-specific behavior.
