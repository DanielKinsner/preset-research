# HANDOFF — preset-research

_Written 2026-06-17 for picking the project up on a new machine / new agent session._

This is the onboarding doc. After reading it, **`STATUS.md` is the live state**
and `README.md` is the reference. Everything described here is committed and
pushed to `origin` (github.com/DanielKinsner/preset-research), **including all
audio** — a fresh clone has the complete dataset.

---

## 1. What this project is

Scientifically measuring what online mastering services do to audio through their
presets. We upload **spectrally-neutral test signals**, download the mastered
outputs, and measure the **input→output delta**. Neutral input gives the adaptive
engine nothing track-specific to react to, so the delta isolates each preset's
**static processing character** — its fingerprint.

- **Operator (Dan):** uploads signals to the service, selects preset, downloads
  WAVs, drops them in `competitors/`. Records the suggested input gain.
- **Agent (you):** all analysis, measurement, reporting, repo upkeep.

The thesis in one line: *input is neutral by design, so whatever changed in the
output is the preset.*

## 2. Set up on the new machine

```bash
git clone https://github.com/DanielKinsner/preset-research.git
cd preset-research
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt      # Windows
# .venv/bin/python  -m pip install -r requirements.txt       # macOS/Linux
```

The `.venv` is **not** committed (gitignored) — recreate it as above. The audio
**is** committed, so you have everything else. Verify the toolchain:

```bash
.venv\Scripts\python tools\validate_signals.py     # expect 8/8 PASS
.venv\Scripts\python tools\fingerprint.py --service bandlab
.venv\Scripts\python tools\compare.py  --service bandlab
```

Then open `reports/fingerprints/bandlab/comparison.html`.

### 2b. Completing the matrix (masters downloaded on this machine)

The remaining signals are downloaded on whichever machine you're on now
(`pink_noise_minus10`, `click_track`, `dynamic_test_minus14`,
`mid_side_test_minus20` — each × 8 presets = 32 files). Drop each into
`competitors/bandlab/<preset>/`, keeping the source stem in the filename
(e.g. `click_track-oomph.wav`). Then:

```bash
.venv\Scripts\python tools\fingerprint.py --service bandlab   # ingests new files
.venv\Scripts\python tools\compare.py  --service bandlab
git add -A          # competitor WAVs are tracked now, so this sweeps them in
git commit -m "Add <signal> masters"
git push
```

**Pushing from a new machine needs GitHub auth set up** (PAT via Git Credential
Manager, `gh auth login`, or an SSH remote). Verify first: `git ls-remote origin`
should list refs without erroring. Without push access, new masters stay stranded
locally — the same trap we hit on the first machine.

Also: record the BandLab **suggested input gain** for each new signal before
zeroing it, and add it to `competitors/bandlab/capture.json` under `per_signal`
(set `status: confirmed`). `click_track` is the acid test — the −4.5 dBFS peak
model predicts ≈ −4.1; a large positive value instead would mean loudness-aware
gain.

## 3. Current state (2026-06-17)

**Tooling: complete and verified.**
- `tools/signals.py` — ground-truth registry for the 8 test signals.
- `tools/audio_metrics.py` — core library; one canonical record per file
  (levels, true-peak, LUFS/LRA, 9-band energy, slope, centroid, stereo, +
  per-signal analyzers). Tone/dynamic analyzers align to content onset.
- `tools/validate_signals.py` — Step 1, **8/8 PASS / 66 checks**.
- `tools/fingerprint.py` — Step 3, input→output deltas + per-preset aggregate +
  service `canonical.json`. Self-test passes.
- `tools/report.py` — validation HTML report.
- `tools/compare.py` — preset comparison HTML (EQ-contour overlay + loudness/
  limiting ranking).

**Data captured so far: 4 of 8 signals × 8 presets = 32 masters.**
- Signals done (all 8 presets): `pink_noise_minus20`, `pink_noise_minus14`,
  `sine_sweep_minus20`, `tone_ladder_minus20`.
- Signals still to upload (Dan finishing before handoff): `pink_noise_minus10`,
  `click_track`, `tone…` done, `dynamic_test_minus14`, `mid_side_test_minus20`.
- Presets (8): `universal · clarity · oomph · tape · spatial · natural · warm · punch`.
- Full target matrix: 8 signals × 8 presets = **64 masters**.

> **If 64 masters are present when you start:** just re-run the three commands in
> §2 — `fingerprint.py` ingests whatever is there; nothing else needed.

## 4. The locked capture protocol (do not change without recording it)

Every upload, identical: **input gain = 0 (decline BandLab's suggestion)** ·
**intensity = Normal (50%)**. Filenames keep the source stem as a substring
(e.g. `tone_ladder_minus20-oomph.wav`) so outputs auto-match their input.
Full provenance + per-signal suggested gains live in
`competitors/bandlab/capture.json` and are stamped into every measurement.

Why gain 0: feeds known native levels so the −20/−14/−10 pink series probes
level-dependence. Accepting the suggestion would peak-normalize them to a common
level and collapse that experiment.

## 5. Findings to date (all from `measurements/fingerprints/bandlab/`)

1. **BandLab's suggested input gain is a peak normalizer to ≈ −4.5 dBFS —
   CONFIRMED on all 8 signals** (`suggested = −4.5 − input_peak_dbfs`, max error
   0.05 dB; full table in `capture.json`). The decisive `click_track` acid test
   passed: sparse signal (peak −0.45, RMS −44), suggestion **−4.1** = peak-target —
   a loudness target would have demanded ~+30 dB. Recorded suggestions:
   −20→+2.5, −14→−3.9, −10→−4.5, sweep→+13.5, tone→+13.5, mid/side→+11.3,
   click→−4.1, dynamic→−4.5. It conditions for **headroom, not loudness**, is
   computed from the input file (same across presets), and we **decline it (gain 0)**
   on every upload. Because the source signals are all ≤ 0 dBFS, declining the gain
   can never clip the input.
2. **Processing is level-dependent (adaptive).** Makeup gain differs by input
   level — e.g. oomph: **+8.2 dB @ −20 vs +3.4 dB @ −14**. So preset EQ curves
   are operating-point snapshots, not universal constants. The −10 pink (still to
   come) adds the third point.
3. **Preset personalities (pink_−20, 8 presets):** loudest/brightest/most-limited
   **punch** (−7.4 LUFS, +12 dB makeup, crest −6.6, clips +1.1 dBTP); gentlest
   **warm** (−13.8 LUFS, +3 dB makeup); only *darkening* preset **natural**;
   **oomph** = +9.7 dB sub (20–60 Hz), independently confirmed by the tone ladder
   at **+15 dB @ 40 Hz**; **clarity** mid-scoop "smile"; **spatial/tape** add air.
4. **5 of 8 presets deliver masters that exceed 0 dBTP** (inter-sample clipping
   on playback): clarity, natural, spatial, universal, punch. Only warm, tape,
   oomph stay under.

### 5b. Implications (carry these into the final analysis)

These are *what the findings mean*, not just the findings:

- **BandLab normalizes at BOTH ends; the "preset" is what's in the middle.** Input
  is peak-conditioned to ≈ −4.5 dBFS; output is driven toward a loudness target
  (that's *why* makeup gain shrinks as the input gets louder — finding #2). The
  preset's true *character* is the EQ / compression / saturation / stereo work
  **between** those two normalizers. When interpreting, separate level-management
  (input peak-cond + output loudness target) from tonal/dynamic character.
- **Our fingerprints describe the chain's raw, level-dependent response — NOT what
  a typical user gets.** A normal user accepts the suggestion, so their track is
  peak-normalized to −4.5 dBFS *first*. We decline it to expose level-dependence.
  Consequence: cross-preset comparisons are clean (same input, bypassed
  uniformly), but absolute "what you'd hear as a user" is the −4.5-normalized
  condition — which our −20/−14 levels **bracket** but don't hit exactly. To get
  it directly, add a "gain-to-−4.5" run, or interpolate between −20 and −14.
- **The −10 pink at gain 0 is an off-design stress test.** It enters at 0 dBFS
  peak — ~4.5 dB hotter than BandLab's normalizer would ever feed the chain. So
  −10 results show "how the preset survives an over-hot input," useful for
  robustness but *not* normal operation. Label it as such in the writeup.
- **To emulate a preset faithfully, the recipe includes the input stage:**
  peak-normalize to −4.5 dBFS → apply the preset's EQ/comp/stereo fingerprint →
  drive output to its loudness target. The input conditioning is part of the
  chain, not a preamble to ignore.
- **The input stage is now fully pinned down.** The click_track acid test returned
  −4.1 → the input conditioning is a pure, exactly-modelable peak normalizer to
  −4.5 dBFS (not content-dependent). In any emulation it's a deterministic pre-gain,
  not an approximation.
- **"Adaptive" has two layers here.** Even with neutral signals we've already
  caught level-adaptivity (the normalizers). The *content*-adaptivity (track-aware
  EQ/comp that reacts to real music) is the separate, future investigation — don't
  conflate the two in the analysis.

## 6. Repo map

```
source/test-signals/     8 neutral WAVs (committed constants; never regenerate)
competitors/bandlab/<preset>/   mastered outputs (NOW committed — see §8)
  capture.json           locked protocol + suggested-gain log + auto-gain model
measurements/
  validation/            per-signal validation JSON + summary
  fingerprints/bandlab/  per-pair + per-preset fingerprint.json + canonical.json
reports/
  validation/            validation-report.html
  fingerprints/bandlab/  comparison.html + comparison.md
tools/                   signals, audio_metrics, validate_signals, fingerprint,
                         report, compare
requirements.txt · README.md · STATUS.md · HANDOFF.md
```

The **agent-canonical dataset** is `measurements/fingerprints/bandlab/canonical.json`
— full measurements, deltas, methodology, signal provenance, and capture protocol
in one file. Read it to make DSP decisions without re-analyzing audio.

## 7. What's next (priority order)

1. **Finish the matrix** — fingerprint the remaining signals once present
   (pink_−10, click_track, dynamic_test, mid_side_test × 8 presets), then re-run
   compare. (pink_−10 completes the 3-point level-dependence curve;
   mid_side reveals the stereo-width behavior — esp. for `spatial`; click reveals
   limiter attack/release.)
2. **Extend `compare.py`** with sections for the data already captured but not yet
   visualized: per-frequency gain (tone ladder), level-dependence overlay
   (−20/−14/−10 contours per preset), dynamics, stereo width, limiter timing.
   Sections are gated on signal presence, so they activate automatically.
3. **Other services** (LANDR, eMastered, CloudBounce) — registry/engine are
   service-agnostic; just add `competitors/<service>/` and a `capture.json`.
   (The −4.5 dBFS auto-gain model is confirmed on all 8 signals — done.)

## 8. Key decisions & gotchas

- **All audio is committed now** (override of the original spec, which gitignored
  competitor masters). This keeps the full dataset portable — a clone has
  everything. If the corpus grows large (the full matrix + more services), migrate
  WAVs to **Git LFS** to keep git history lean.
- **`source/original-references/`** (the ~344 MB real-music masters) was removed by
  the operator; the old gitignore rule is gone.
- **BandLab outputs run 0.01–0.42 s long** (lead-in/tail). Harmless for broadband
  metrics; tone/dynamic analyzers align to content onset (`audio_metrics.content_onset`).
  Apply the same alignment if you add other segment-timed analyses.
- **Windows/NTFS:** glob `*.wav` and `*.WAV` match the same file — iterate and
  filter by `suffix.lower()` (already fixed in fingerprint.py).
- **Line endings:** repo is LF (`.gitattributes`); scripts write outputs with
  `newline="\n"`. Keep it that way.
- **EQ views:** `eq_contour_db` (mean-centered, the readable "EQ curve"),
  `eq_shape_db` (makeup-gain-relative), `eq_band_delta_raw_db` (raw) all stored.
```
