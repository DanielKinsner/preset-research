# YES Master loudness-parity vs BandLab fingerprint gap analysis

Generated: 2026-06-18T17:09:07.917247Z

This is a measurement/reporting run only. It did not change YES Master DSP, preset calibration, UI, export behavior, or product code.

## What this rerun controls

- The first YES corpus held every preset near `-14 LUFS`; that made BandLab loudness differences dominate some comparisons.
- This corpus gives each YES preset a role-matched BandLab target LUFS: Universal->Universal, Clarity->Clarity, Tape->Tape, Spatial->Spatial, Oomph->Oomph, Warmth->Warm, Punch/Loud->Punch, Custom->Natural.
- The render still uses YES Master engine behavior, `-1 dBTP` ceiling, Volume Match off, input gain `0`, intensity `0.5`, and source sample rate/bit depth.
- If YES cannot reach a BandLab target under that ceiling/chain, the measured shortfall is itself the result.

## Capture validation

- YES parity renders: `9 presets x 8 signals = 72 WAVs`.
- Every render is `44.1 kHz`, `16-bit`, stereo, 60 seconds.
- Fingerprints written to `measurements/fingerprints/yesmaster-loudness-parity/canonical.json`.

## Headline findings

- Nearest BandLab neighbors after role loudness parity are: clarity, universal, warm. This is more varied than the fixed `-14 LUFS` run, so loudness was a major confound in the first distance ranking.
- YES Punch still does not reach BandLab Punch: it remains -3.06 LU, +4.93 dB dynamic contrast, -12.48 dB width, and -3.35 LU click lift relative to BandLab Punch.
- YES Loud also remains below the BandLab Punch role target: -2.30 LU, +1.98 dB dynamics, and -12.51 dB width relative to BandLab Punch.
- Spatial gets much closer in output loudness, but not in width: YES Spatial is -0.41 LU and -14.37 dB width relative to BandLab Spatial.
- Custom did not move toward BandLab Natural loudness in this run; it remains -2.20 LU below Natural, suggesting the neutral Custom chain/guardrails resist that target on this synthetic corpus.

## Nearest measured BandLab neighbors

| YES preset | Nearest BandLab | Distance | Top 3 |
| --- | --- | --- | --- |
| clarity | warm | 3.36 | warm 3.36, clarity 6.35, tape 8.77 |
| custom | warm | 4.29 | warm 4.29, clarity 4.42, universal 7.32 |
| loud | universal | 5.88 | universal 5.88, tape 6.11, spatial 6.48 |
| oomph | clarity | 4.50 | clarity 4.50, warm 4.71, natural 6.74 |
| punch | universal | 4.56 | universal 4.56, tape 4.58, spatial 5.64 |
| spatial | clarity | 4.35 | clarity 4.35, tape 4.39, warm 4.87 |
| tape | clarity | 4.29 | clarity 4.29, tape 4.50, warm 4.73 |
| universal | warm | 3.91 | warm 3.91, clarity 4.73, tape 6.11 |
| warmth | warm | 2.87 | warm 2.87, clarity 5.60, natural 7.59 |

## Named / role counterpart gaps

Deltas are YES minus BandLab. Negative LUFS delta means YES still rendered quieter after parity targeting. Positive dynamics delta means YES compressed less.

| YES preset | BandLab ref | Distance | LUFS delta | Dynamics delta dB | Corr delta | Width delta dB | Click lift delta LU | Largest EQ gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universal | universal | 6.54 | -0.05 | +3.99 | +0.006 | -2.01 | +3.03 | 20-60 Hz -2.44, 2-4k Hz +1.05, 250-500 Hz +0.74 |
| clarity | clarity | 6.35 | -0.05 | +2.40 | +0.008 | -2.27 | +3.07 | 20-60 Hz -4.23, 1-2k Hz +1.48, 500-1k Hz +1.36 |
| tape | tape | 4.50 | -0.05 | +2.00 | +0.023 | -4.59 | +2.44 | 2-4k Hz +2.59, 8-16k Hz -1.58, 20-60 Hz -1.07 |
| spatial | spatial | 6.30 | -0.41 | +2.84 | +0.309 | -14.37 | +3.86 | 20-60 Hz -1.31, 8-16k Hz -0.88, 2-4k Hz +0.76 |
| oomph | oomph | 7.53 | -0.04 | +4.68 | +0.005 | -1.64 | +5.51 | 20-60 Hz -7.83, 120-250 Hz +3.33, 250-500 Hz +2.36 |
| warmth | warm | 2.87 | -0.04 | -0.60 | +0.008 | -2.92 | +2.67 | 20-60 Hz +3.06, 8-16k Hz -1.79, 1-2k Hz -0.88 |
| punch | punch | 11.80 | -3.06 | +4.93 | +0.124 | -12.48 | -3.35 | 8-16k Hz -5.52, 4-8k Hz -4.50, 500-1k Hz +4.16 |
| loud | punch | 10.19 | -2.30 | +1.98 | +0.124 | -12.51 | -2.79 | 8-16k Hz -5.13, 20-60 Hz -4.97, 500-1k Hz +4.35 |
| custom | natural | 7.78 | -2.20 | +5.41 | +0.003 | -1.37 | -0.43 | 4-8k Hz +2.10, 120-250 Hz -1.82, 2-4k Hz +1.75 |

## Agent-canonical retune notes

The companion JSON keeps the raw per-band and per-metric deltas. Candidate directions are deliberately marked `do_not_apply_automatically: true`; these are research results, not calibration changes.

### universal -> BandLab universal

- YES compresses less than BandLab by 3.99 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.006, width delta -2.01 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.03 LU harder; candidate direction is less sparse-transient lift.
- Tonal contour is lower in sub/low bass by -1.35 dB on average; candidate direction is more sub/low bass.

### clarity -> BandLab clarity

- YES compresses less than BandLab by 2.41 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.008, width delta -2.27 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.07 LU harder; candidate direction is less sparse-transient lift.
- Tonal contour is lower in sub/low bass by -2.19 dB on average; candidate direction is more sub/low bass.

### tape -> BandLab tape

- YES compresses less than BandLab by 2.00 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.023, width delta -4.59 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.44 LU harder; candidate direction is less sparse-transient lift.

### spatial -> BandLab spatial

- YES compresses less than BandLab by 2.84 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.309, width delta -14.37 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.86 LU harder; candidate direction is less sparse-transient lift.

### oomph -> BandLab oomph

- YES compresses less than BandLab by 4.68 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES pulls sparse clicks 5.51 LU harder; candidate direction is less sparse-transient lift.
- Tonal contour is lower in sub/low bass by -3.45 dB on average; candidate direction is more sub/low bass.
- Tonal contour is higher in bass/low mid by +2.84 dB on average; candidate direction is less bass/low mid.

### warmth -> BandLab warm
Note: BandLab label is warm; YES label is warmth.

- YES is narrower/less decorrelated than BandLab: correlation delta +0.008, width delta -2.92 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.67 LU harder; candidate direction is less sparse-transient lift.
- Tonal contour is higher in sub/low bass by +1.30 dB on average; candidate direction is less sub/low bass.
- Tonal contour is lower in air/top by -1.33 dB on average; candidate direction is more air/top.

### punch -> BandLab punch

- Even in loudness-parity mode, YES remains 3.05 LU below BandLab punch; the likely gap is chain/headroom/limiting behavior, not merely target selection.
- YES compresses less than BandLab by 4.93 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.124, width delta -12.48 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.35 LU less; candidate direction is more sparse-transient lift.
- Tonal contour is lower in sub/low bass by -1.72 dB on average; candidate direction is more sub/low bass.

### loud -> BandLab punch
Note: BandLab has no Loud preset in this corpus; Punch is used as the closest high-energy BandLab reference.

- Even in loudness-parity mode, YES remains 2.30 LU below BandLab punch; the likely gap is chain/headroom/limiting behavior, not merely target selection.
- YES compresses less than BandLab by 1.98 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.124, width delta -12.51 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.79 LU less; candidate direction is more sparse-transient lift.
- Tonal contour is lower in sub/low bass by -2.34 dB on average; candidate direction is more sub/low bass.

### custom -> BandLab natural
Note: YES Custom is the neutral custom calibration; BandLab Natural is the closest neutral-labeled reference. YES Custom did not reach the Natural LUFS target under this chain.

- Even in loudness-parity mode, YES remains 2.20 LU below BandLab natural; the likely gap is chain/headroom/limiting behavior, not merely target selection.
- YES compresses less than BandLab by 5.41 dB on the dynamic test; candidate direction is more density/compression if matching BandLab is desired.
- Tonal contour is higher in air/top by +1.70 dB on average; candidate direction is less air/top.

## Output artifacts

- `competitors/yesmaster-loudness-parity/capture.json` plus 72 parity WAV renders.
- `measurements/fingerprints/yesmaster-loudness-parity/canonical.json`.
- `reports/fingerprints/yesmaster-loudness-parity/comparison.html` and `.md`.
- `reports/fingerprints/yesmaster-loudness-parity-vs-bandlab/gap-analysis.md`.
- `reports/fingerprints/yesmaster-loudness-parity-vs-bandlab/agent-canonical.json`.
