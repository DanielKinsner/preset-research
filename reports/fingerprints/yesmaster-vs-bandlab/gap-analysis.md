# YES Master vs BandLab preset fingerprint gap analysis

Generated: 2026-06-18T16:53:32.139030Z

This is a measurement/reporting run only. It did not change YES Master DSP, preset calibration, UI, export behavior, or product code.

## What was measured

- YES Master renders: 9 current presets x 8 BandLab-method test signals = 72 WAVs in `competitors/yesmaster/`.
- Capture validation: every YES render is 44.1 kHz, 16-bit, stereo, 60 seconds; `capture.json` has 72 renders.
- Fingerprints: `measurements/fingerprints/yesmaster/canonical.json` and existing `measurements/fingerprints/bandlab/canonical.json`.
- YES protocol: input gain 0 dB, intensity 0.5, Volume Match off, Custom delivery, -14 LUFS target, -1 dBTP ceiling, source sample rate/bit depth.
- Important caveat: BandLab outputs are unconstrained service renders, while YES was deliberately held at -14 LUFS. Loudness gaps are real under this protocol, but they are not automatic retune instructions.

## Headline findings

- Under the controlled -14 LUFS YES protocol, every YES preset's nearest measured BandLab neighbor is in this set: warm. In practice, all YES presets cluster near BandLab's quieter/least-processed region, not BandLab's aggressive presets.
- BandLab Punch is much more aggressive than YES Punch: YES Punch is -6.66 LU, +4.92 dB dynamic-contrast change, -12.48 dB width change, and -3.35 LU click-lift relative to BandLab Punch.
- YES Loud is also far from BandLab's high-energy Punch behavior: -6.66 LU quieter, -12.51 dB narrower, and -2.79 LU lower click lift than BandLab Punch.
- The biggest single role gap is Spatial: YES Spatial is +0.309 correlation-change units and -14.37 dB width below BandLab Spatial, while also -3.72 LU quieter.
- Oomph does not match BandLab Oomph's behavior: YES Oomph is +4.68 dB less compressed and +5.51 LU higher on sparse clicks, while its largest EQ gap is 20-60 Hz -7.83 dB.
- The closest named counterpart is Warmth vs BandLab Warm by this distance heuristic; even there, YES still pulls sparse clicks harder and is narrower in the mid/side test.

## Nearest measured BandLab neighbors

Distance is a transparent ranking heuristic from EQ/tone RMSE, loudness/makeup, dynamics/crest, stereo, click lift, tilt, and density. Lower is closer.

| YES preset | Nearest BandLab | Distance | Top 3 |
| --- | --- | --- | --- |
| clarity | warm | 3.73 | warm 3.73, clarity 7.03, tape 9.59 |
| custom | warm | 4.76 | warm 4.76, clarity 5.03, universal 8.09 |
| loud | warm | 7.19 | warm 7.19, clarity 9.20, natural 9.51 |
| oomph | warm | 4.59 | warm 4.59, clarity 5.46, natural 7.84 |
| punch | warm | 4.66 | warm 4.66, clarity 7.34, natural 8.68 |
| spatial | warm | 3.15 | warm 3.15, clarity 6.50, tape 8.89 |
| tape | warm | 3.22 | warm 3.22, clarity 6.56, tape 8.91 |
| universal | warm | 3.42 | warm 3.42, clarity 6.71, tape 9.21 |
| warmth | warm | 2.99 | warm 2.99, clarity 5.88, natural 7.90 |

## Named / role counterpart gaps

Deltas are YES minus BandLab. Negative LUFS delta means YES rendered quieter. Positive dynamics delta means YES compressed less, because the dynamic contrast change is less negative.

| YES preset | BandLab ref | Distance | LUFS delta | Dynamics delta dB | Corr delta | Width delta dB | Click lift delta LU | Largest EQ gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universal | universal | 9.43 | -2.41 | +3.99 | +0.006 | -2.01 | +3.03 | 20-60 Hz -2.44, 2-4k Hz +1.05, 250-500 Hz +0.74 |
| clarity | clarity | 7.03 | -0.63 | +2.40 | +0.008 | -2.27 | +3.07 | 20-60 Hz -4.23, 1-2k Hz +1.48, 500-1k Hz +1.36 |
| tape | tape | 8.91 | -3.34 | +2.00 | +0.023 | -4.59 | +2.44 | 2-4k Hz +2.59, 8-16k Hz -1.58, 20-60 Hz -1.07 |
| spatial | spatial | 10.54 | -3.72 | +2.84 | +0.309 | -14.37 | +3.86 | 20-60 Hz -1.31, 8-16k Hz -0.88, 2-4k Hz +0.76 |
| oomph | oomph | 8.21 | -1.00 | +4.68 | +0.005 | -1.64 | +5.51 | 20-60 Hz -7.83, 120-250 Hz +3.33, 250-500 Hz +2.36 |
| warmth | warm | 2.99 | -0.27 | -0.60 | +0.008 | -2.92 | +2.67 | 20-60 Hz +3.06, 8-16k Hz -1.79, 1-2k Hz -0.88 |
| punch | punch | 16.68 | -6.66 | +4.92 | +0.124 | -12.48 | -3.35 | 8-16k Hz -5.52, 4-8k Hz -4.50, 500-1k Hz +4.16 |
| loud | punch | 16.09 | -6.66 | +1.98 | +0.124 | -12.51 | -2.79 | 8-16k Hz -5.13, 20-60 Hz -4.97, 500-1k Hz +4.35 |
| custom | natural | 8.42 | -2.20 | +5.41 | +0.003 | -1.37 | -0.43 | 4-8k Hz +2.10, 120-250 Hz -1.82, 2-4k Hz +1.75 |

## Agent-canonical retune notes

The companion JSON contains per-preset constants, metric deltas, per-band EQ deltas, tone-ladder deltas, and candidate adjustment directions. Those directions are intentionally marked `do_not_apply_automatically: true`; they are evidence for a future owner/listening decision, not a change request.

### universal -> BandLab universal

- YES is 2.41 LU quieter than BandLab universal; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 3.99 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.006, width delta -2.01 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.03 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.
- Tonal contour is lower in sub/low bass by -1.35 dB on average; candidate direction is more sub/low bass.

### clarity -> BandLab clarity

- YES compresses less than BandLab by 2.41 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.008, width delta -2.27 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.07 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.
- Tonal contour is lower in sub/low bass by -2.19 dB on average; candidate direction is more sub/low bass.

### tape -> BandLab tape

- YES is 3.34 LU quieter than BandLab tape; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 2.00 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.023, width delta -4.59 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.44 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.

### spatial -> BandLab spatial

- YES is 3.72 LU quieter than BandLab spatial; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 2.84 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.309, width delta -14.37 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.86 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.

### oomph -> BandLab oomph

- YES is 1.00 LU quieter than BandLab oomph; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 4.68 dB on the dynamic test; candidate direction is more density/compression.
- YES pulls sparse clicks 5.51 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.
- Tonal contour is lower in sub/low bass by -3.45 dB on average; candidate direction is more sub/low bass.
- Tonal contour is higher in bass/low mid by +2.84 dB on average; candidate direction is less bass/low mid.

### warmth -> BandLab warm
Note: BandLab label is warm; YES label is warmth.

- YES is narrower/less decorrelated than BandLab: correlation delta +0.008, width delta -2.92 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.67 LU harder; candidate direction is less transient/sparse-material lift if matching BandLab.
- Tonal contour is higher in sub/low bass by +1.30 dB on average; candidate direction is less sub/low bass.
- Tonal contour is lower in air/top by -1.33 dB on average; candidate direction is more air/top.

### punch -> BandLab punch

- YES is 6.66 LU quieter than BandLab punch; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 4.93 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.124, width delta -12.48 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 3.35 LU less; candidate direction is more transient/sparse-material lift if matching BandLab.
- Tonal contour is lower in sub/low bass by -1.72 dB on average; candidate direction is more sub/low bass.

### loud -> BandLab punch
Note: BandLab has no Loud preset in this corpus; Punch is used as the closest high-energy BandLab reference.

- YES is 6.66 LU quieter than BandLab punch; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 1.98 dB on the dynamic test; candidate direction is more density/compression.
- YES is narrower/less decorrelated than BandLab: correlation delta +0.124, width delta -12.51 dB; candidate direction is more stereo width/decorrelation.
- YES pulls sparse clicks 2.79 LU less; candidate direction is more transient/sparse-material lift if matching BandLab.
- Tonal contour is lower in sub/low bass by -2.34 dB on average; candidate direction is more sub/low bass.

### custom -> BandLab natural
Note: YES Custom is the neutral custom calibration; BandLab Natural is the closest neutral-labeled reference.

- YES is 2.20 LU quieter than BandLab natural; if matching BandLab output behavior, consider a higher target loudness for this preset/protocol. candidate only; do not apply without owner listening signoff.
- YES compresses less than BandLab by 5.41 dB on the dynamic test; candidate direction is more density/compression.
- Tonal contour is higher in air/top by +1.70 dB on average; candidate direction is less air/top.

## Output artifacts

- `competitors/yesmaster/capture.json` plus 72 YES Master WAV renders.
- `measurements/fingerprints/yesmaster/canonical.json`.
- `reports/fingerprints/yesmaster-vs-bandlab/gap-analysis.md`.
- `reports/fingerprints/yesmaster-vs-bandlab/agent-canonical.json`.
