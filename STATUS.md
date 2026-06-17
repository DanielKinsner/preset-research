# STATUS — read this first

_Last updated: 2026-06-16 · the single source of truth for "where are we."_
_New machine? Read `HANDOFF.md` first._

> **MILESTONE (2026-06-16): the full 8×8 matrix is complete and verified.** All 64
> masters fingerprinted; `compare.py` extended with all 5 new sections; findings
> adversarially re-checked against the raw per-pair JSONs (6 verifiers + critic).
> Two pre-commit corrections came out of that pass — see "Findings" and "Corrections".

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
- [x] **Real fingerprints + comparison** — **all 8 signals × 8 presets = 64 masters
      measured** (full matrix complete 2026-06-16).
      `tools/compare.py` → `reports/fingerprints/bandlab/comparison.html`.
      Canonical: `measurements/fingerprints/bandlab/canonical.json`.
- [x] **Onset alignment** added to tone/dynamic analyzers
      (`audio_metrics.content_onset`) — handles BandLab's 0.01–0.42 s lead-in.
      Validation still 8/8 PASS.
- [x] **`compare.py` extended** with the 5 data-gated sections that the later signals
      unlock: per-frequency tone gain, level-dependence (LUFS) curve, dynamics, stereo
      width, and click-track transient handling. 8 charts render.
- [x] **Findings adversarially verified** (2026-06-16) against the raw per-pair JSONs:
      6 per-dimension skeptics + a completeness critic. Caught & fixed two issues before
      commit (see **Corrections** below).

## Scope: 8 BandLab presets

`universal · clarity · oomph · tape · spatial · natural · warm · punch`
Full matrix = 8 signals × 8 presets = **64 masters**.

## Waiting on operator (Dan)

- [x] **All 8 signals × 8 presets = 64 masters captured, fingerprinted, compared, verified.**
      The BandLab matrix is **complete**. All 8 suggested input gains are recorded and
      confirmed in `capture.json` (the −4.5 dBFS peak-normalizer model is proven on all 8,
      `click_track` acid test passed). Nothing is pending from the operator for BandLab.
- [ ] **Optional follow-ups (operator captures, not blockers)** — see "Future work":
      a **dense-transient signal** (drum loop / shaped bursts) for real limiter timing
      (the click track cannot measure it — see Corrections), **more stereo signals** (the
      whole battery has only one non-mono signal), and the **intensity sweep** (0/50/100%).

## Next (agent, as signals arrive)

1. `tools/fingerprint.py --service bandlab` then `tools/compare.py --service bandlab`.
2. **Add onset alignment** to the tone/click/dynamic *output* analyzers — BandLab
   outputs run 0.01–0.42 s long (lead-in/tail), harmless for pink/broadband but it
   offsets segment-timed analyses. Detect content start before windowing.
3. `compare.py` already gates sections on signal presence — per-frequency gain,
   dynamics, stereo width, and limiter timing light up automatically as their
   signals land.

## Findings so far (BandLab) — full 8×8 matrix, adversarially verified

All numbers from `measurements/fingerprints/bandlab/canonical.json`; chart:
`reports/fingerprints/bandlab/comparison.html`. Each finding below survived a
per-dimension skeptic re-deriving it from the raw per-pair JSONs.

- **Tonal/loudness fingerprint (pink_−20, 8 presets) — confirmed unchanged.** Loudest
  **punch** (−7.4 LUFS, +12 dB RMS makeup, crest −6.6 = heaviest limiting, +1.1 dBTP);
  gentlest **warm** (−13.8 LUFS, +3 dB makeup, −3.6 dBTP). Brightest **punch**
  (+2.18 dB/oct); only *darkening* preset on broadband signals **natural** (−0.26).
  Signatures: **oomph** +9.7 dB sub (20–60 Hz), **clarity** mid-scoop "smile,"
  **spatial/tape** high-air lift, **universal** near-flat. **5 of 8 exceed 0 dBTP**
  on pink_−20 (inter-sample clipping): clarity, natural, spatial, universal, punch.
- **Level dependence is a loudness chase — measure it in LUFS, not RMS.** Across pink
  −20 → −14 → −10, every preset's loudness lift FALLS as the input gets hotter (it
  drives toward a loudness target rather than applying fixed gain). Net LUFS drop:
  **punch −7.45 LU (hardest chaser)** … **warm −3.15 LU (least)**. Only **warm** is
  genuinely non-monotonic in LUFS (small dip at −14). ⚠️ The `makeup_gain` field is an
  **RMS** delta, not loudness — on warm it reads +3.0/−1.4/+0.1 dB (looks like
  *attenuation*) while the true LUFS lift is +6.6/+2.2/+3.5 LU. warm trades sub for
  highs, so RMS falls while loudness rises. Use `loudness_lift_lufs_by_input_level`.
- **Dynamics: all 8 compress; correlated with loudness but NOT a mirror.** Every
  `contrast_change_db` is negative — punch crushes most (−11.9 dB), warm least (−3.7).
  Compression intensity is *strongly but imperfectly* correlated with loudness
  (Pearson r ≈ −0.79 vs makeup, −0.76 vs output LUFS). Endpoints match (punch =
  loudest + most-compressing; warm = quietest + least), but the middle diverges:
  **oomph** is 2nd-most-compressing yet only 5th–6th by loudness.
- **Stereo: spatial is the widener, punch second — by both metrics.** spatial
  correlation_change −0.315 / width +16.8 dB; punch −0.124 / +12.7; others modest.
  ⚠️ `correlation_change` is the trustworthy metric: the mid/side source is near-mono
  (side ~24 dB below mid) so width-in-dB rides a low floor and overstates swings.
  Also: mid/side is the **only non-mono signal** in the battery, so stereo conclusions
  rest on one input.
- **Tone ladder cross-validates the pink EQ** (Pearson r +0.69 … +0.95 across 9 bands).
  Strong on oomph (+0.89, sub spike +15 dB @ 40 Hz) and natural (+0.95). punch is the
  weakest (+0.69): the tone ladder shows a **U-shape** (sub boost @ 40 Hz *and* high
  rise) that the shape-normalized pink contour hides — the expected signature of
  **density-dependent / multiband** EQ, not a contradiction.
- **Multiband-density index (pink tilt − sweep tilt):** punch 1.38 (most
  density-dependent) → **natural 0.018 (essentially linear / transparent EQ)**. natural
  is the only preset whose EQ doesn't change with broadband density.
- **Auto input-gain is a peak normalizer to −4.5 dBFS — CONFIRMED on all 8 signals.**
  `suggested = −4.5 − input_peak_dbfs` (max error 0.05 dB). `click_track` acid test
  passed: −4.1 = peak-target, not loudness-aware → conditions for **headroom, not
  loudness**. We decline it (gain 0). Full table in `competitors/bandlab/capture.json`.
- **Intensity default = "Normal" = 50%** of a 0–100% range. We run v1 here. Intensity
  sweep (0/50/100) is Phase 2; intensity-0 doubles as a rig self-check.

### Personalities at a glance (the surprises)

- **warm is the opposite of its name on the numbers.** It *cuts* 20–60 Hz and lifts
  everything above (biggest boosts 4–16 kHz): tilt +0.41 dB/oct, centroid +743 Hz. It
  is the gentlest on loudness/limiting, but tonally it **brightens**, it doesn't warm.
- **natural is the only "transparent" preset** — density-independent EQ (index 0.018),
  consistently *darkening* on every broadband signal (−0.13…−0.28 dB/oct).
- **oomph's two tonal metrics disagree by design:** tilt +0.32 dB/oct (slightly
  brighter) but centroid −2027 Hz (much darker). Its +9.7 dB sub boost dominates the
  energy-weighted centroid while the flat regression tilt doesn't see it. **Report both.**
- **punch chases loudness on every axis:** loudest, most-compressing, brightest,
  hardest level-chaser, and the **only** preset that meaningfully lifts the sparse
  click track (+7.6 LU; next is +1.1).

## Corrections (from the 2026-06-16 verification pass)

1. **Limiter timing was REFUTED and removed.** The old "median transient peak / release"
   metric on the click track did **not** measure limiting — it tracked how much each
   preset *widens* a 1-sample click through the 1 ms envelope. All presets actually let
   clicks reach the ceiling; only **universal (+0.87 dBTP) and warm (+0.82)** clip. punch
   does *not* clip clicks (−1.2 dBTP) despite being loudest. The "Limiter timing" section
   is replaced by **"Click-track transient handling"** showing the two honest metrics
   (output true-peak; click loudness lift). **Real limiter timing needs a dense-transient
   source** — the sparse click train cannot provide it.
2. **`makeup_gain_db` is RMS, not loudness.** Documented inline in `canonical.json`;
   `level_dependence` now carries both `makeup_gain_rms_by_input_level` and
   `loudness_lift_lufs_by_input_level`. Narrative + the level-dependence chart now use LUFS.

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

- **Dense-transient signal for real limiter timing** — a drum loop or shaped tone
  bursts. The 1-sample click train cannot measure attack/release (see Corrections #1).
- **More non-mono signals** — the battery has exactly one (mid/side), so stereo
  behavior is undersampled. Add decorrelated-noise / panned-content tests.
- **Intensity sweep (0/50/100%)** — Phase 2; intensity-0 doubles as a rig self-check.
- Additional services (LANDR, eMastered, CloudBounce) — same methodology, new
  dir under `competitors/`. Registry/engine already service-agnostic.
- Adaptive profiling with diverse real music to isolate track-specific behavior.
