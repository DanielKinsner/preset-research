# preset-research

Scientifically measuring how online mastering services process audio through
their presets. We upload **spectrally-neutral test signals**, download the
mastered outputs, and measure the input→output **delta**. Because the signals
give an adaptive engine nothing track-specific to react to, that delta isolates
each preset's **static processing character** — its fingerprint.

> Input is neutral by design. Whatever changed in the output is the preset.

---

## How it works

```
test signal  ──upload──►  mastering preset  ──download──►  mastered output
   (input)                                                     (output)
        └──────────────────  measure both  ──────────────────────┘
                                   │
                            delta = fingerprint
```

Eight neutral signals each probe a different dimension (tonal balance,
level-dependence, dynamics, stereo, transient handling). See
[`source/test-signals`](source/test-signals) and the registry in
[`tools/signals.py`](tools/signals.py) for the exact ground-truth spec of each.

## Repository layout

```
preset-research/
├── source/test-signals/      8 neutral WAVs — fixed scientific constants (committed)
├── source/original-references/  real-music masters for future work (gitignored, ~344 MB)
├── competitors/<service>/<preset>/   mastered outputs you drop here (audio gitignored)
├── measurements/
│   ├── validation/           per-signal validation JSON + summary.json (committed)
│   └── fingerprints/<service>/<preset>/  per-pair + aggregate fingerprints (committed)
├── reports/validation/       human-readable HTML + markdown (committed)
├── tools/                    measurement code
│   ├── signals.py            ground-truth registry (single source of truth)
│   ├── audio_metrics.py      core measurement library (one canonical record/file)
│   ├── validate_signals.py   Step 1 — validate the 8 signals
│   ├── fingerprint.py        Step 3 — input→output delta + per-preset aggregate
│   └── report.py             Step 4 — human-readable validation report
├── requirements.txt
└── STATUS.md                 what's done / what's next (read this first each session)
```

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt    # Windows
# .venv/bin/python  -m pip install -r requirements.txt     # macOS/Linux
```

## Commands

```bash
# Validate the 8 source signals (calibrates the measurement instrument)
.venv/Scripts/python tools/validate_signals.py

# Render the human-readable validation report
.venv/Scripts/python tools/report.py

# Fingerprint mastered outputs once they're in competitors/<service>/<preset>/
.venv/Scripts/python tools/fingerprint.py --service bandlab

# Prove the delta math on a synthetic known transform (no service data needed)
.venv/Scripts/python tools/fingerprint.py --self-test
```

## Two output formats (by design)

1. **Human-readable** — `reports/` HTML lab reports with overlay charts and
   PASS/WARN/FAIL tables. Open `reports/validation/validation-report.html` in a
   browser.
2. **Agent-canonical** — `measurements/` JSON. Every file gets one structured
   record (`measure_file`); every preset gets a `fingerprint.json`; each service
   gets a `canonical.json` with full measurements, methodology, and signal
   provenance — enough for another agent to make DSP decisions without
   re-analyzing audio.

## What each fingerprint dimension means

| Dimension | Source signal | What it reveals |
|---|---|---|
| EQ shape (makeup-gain-removed band energy) | pink noise −20 | tonal coloration independent of loudness |
| Spectral tilt / centroid shift | pink noise | brightening vs darkening |
| Per-frequency gain | tone ladder | exact dB at 40 Hz … 16 kHz |
| Level-dependence | pink −20/−14/−10 | whether processing adapts to input level |
| Loudness target + makeup gain | pink noise | how loud the preset pushes (LUFS; `makeup_gain` is RMS — use the LUFS field) |
| Dynamics / crest / LRA change | dynamic test, pink | how much it compresses |
| Click transient handling (true-peak, loudness lift) | click track | do clicks clip; how hard sparse transients are pulled up |
| Stereo width / correlation change | mid/side test | narrowing vs widening (correlation is the trustworthy metric) |
| True-peak ceiling | all | inter-sample clipping headroom |

## Measurement methods

- **Loudness:** EBU R128 / ITU-R BS.1770 integrated LUFS + LRA (`pyloudnorm`).
- **True peak:** ITU-R BS.1770-style 4× polyphase oversampling.
- **Spectrum:** Welch PSD (Hann, 16384, 50% overlap); band energy = Σ(PSD·df).
- **Slope:** least-squares PSD(dB) vs log-f over 50 Hz–16 kHz, per octave.
- **dBFS convention:** 20·log₁₀(x), full scale = 1.0 (full-scale sine = −3.01 dBFS RMS).

## Operator workflow (Dan)

1. Upload a test signal to a service, select a preset, download the WAV.
2. Drop it in `competitors/<service>/<preset>/`. Keep the **source filename as a
   substring** so it auto-matches (e.g. `pink_noise_minus20_master.wav`).
3. Tell the agent; it runs `fingerprint.py` and updates the reports.
4. If a service **rejects** a signal, that's data — note it; rejection reveals
   content-detection gating.
