# bandlab emulation — reconstruction error
_Each preset's **pink_-20-derived** recipe applied to every source signal, compared to the real master. Tonal error = RMS of mean-centered 9-band difference (level-independent tonal shape). Low cross-signal tonal error = the fingerprint is a transferable recipe._

## Bottom line
- **At its operating point (pink_-20) the emulator reconstructs the master near-perfectly:** 0.23 dB tonal RMS, 0.00 LU loudness error. The recipe *is* the preset.
- **The tonal/EQ fingerprint transfers across signal types:** 0.72 dB mean cross-signal tonal error (pink levels, sweep, tone). EQ is the solid, portable dimension.
- **Loudness is operating-point-specific, by design.** The recipe carries the pink_-20 loudness target; applied to a hotter input (pink_-10) it over-drives loudness — that divergence IS the measured level-dependence (the loudness chase), not an emulator fault. Pick the target from `level_dependence` for the actual level.
- **Transients/limiting are NOT modeled** (click_track error is large): the brickwall stand-in hard-clips sparse clicks. Faithful limiter behavior needs a dense-transient capture (see HANDOFF).
- **Hardest preset to emulate = punch** (most cross-signal tonal error), exactly the preset the independent multiband-density index flags as most density-dependent — two methods, one conclusion.

## Mean tonal error by signal (dB)
| Signal | Mean tonal RMS err (dB) | Interpretation |
|---|---|---|
| pink_noise_minus20.wav | 0.23 | self-reference (EQ derived here) — near-zero = filter sane |
| pink_noise_minus14.wav | 0.29 | level transfer (different operating point) |
| pink_noise_minus10.wav | 0.48 | hot-level transfer |
| sine_sweep_minus20.wav | 1.07 | fine frequency transfer |
| tone_ladder_minus20.wav | 1.07 | discrete-tone transfer |
| dynamic_test_minus14.wav | 0.46 | transient material — compression gap shows here |
| mid_side_test_minus20.wav | 0.87 | stereo material |
| click_track.wav | 12.13 | sparse transients — expected worst (no timing model) |

## Full per-preset / per-signal table
| Preset | Signal | Tonal RMS err (dB) | LUFS err | Tilt err (dB/oct) |
|---|---|---|---|---|
| clarity | pink_noise_minus20.wav | 0.14 | -0.00 | +0.00 |
| clarity | pink_noise_minus14.wav | 0.27 | -1.56 | +0.08 |
| clarity | pink_noise_minus10.wav | 0.76 | -6.11 | +0.25 |
| clarity | sine_sweep_minus20.wav | 0.89 | -1.49 | +0.27 |
| clarity | tone_ladder_minus20.wav | 0.95 | -1.90 | -1.98 |
| clarity | dynamic_test_minus14.wav | 0.76 | -6.23 | +0.25 |
| clarity | mid_side_test_minus20.wav | 0.39 | +0.59 | +0.04 |
| clarity | click_track.wav | 15.06 | +15.85 | -5.82 |
| natural | pink_noise_minus20.wav | 0.13 | +0.00 | +0.02 |
| natural | pink_noise_minus14.wav | 0.16 | -1.22 | +0.02 |
| natural | pink_noise_minus10.wav | 0.26 | -5.09 | +0.02 |
| natural | sine_sweep_minus20.wav | 1.29 | -1.26 | +0.38 |
| natural | tone_ladder_minus20.wav | 1.33 | -1.54 | -0.92 |
| natural | dynamic_test_minus14.wav | 0.21 | -2.69 | +0.02 |
| natural | mid_side_test_minus20.wav | 1.30 | -0.60 | +0.07 |
| natural | click_track.wav | 13.59 | +20.67 | -5.42 |
| oomph | pink_noise_minus20.wav | 0.47 | -0.00 | -0.05 |
| oomph | pink_noise_minus14.wav | 0.58 | -1.08 | -0.02 |
| oomph | pink_noise_minus10.wav | 0.73 | -4.39 | +0.07 |
| oomph | sine_sweep_minus20.wav | 0.84 | -1.15 | +0.27 |
| oomph | tone_ladder_minus20.wav | 1.00 | -1.06 | -1.80 |
| oomph | dynamic_test_minus14.wav | 0.73 | -1.92 | +0.05 |
| oomph | mid_side_test_minus20.wav | 0.66 | +1.59 | -0.09 |
| oomph | click_track.wav | 11.48 | +21.72 | -4.08 |
| punch | pink_noise_minus20.wav | 0.23 | -0.02 | -0.02 |
| punch | pink_noise_minus14.wav | 0.27 | -0.74 | +0.02 |
| punch | pink_noise_minus10.wav | 0.46 | -2.75 | +0.11 |
| punch | sine_sweep_minus20.wav | 2.75 | -0.21 | +0.99 |
| punch | tone_ladder_minus20.wav | 2.60 | -0.60 | -1.21 |
| punch | dynamic_test_minus14.wav | 0.42 | -0.70 | +0.10 |
| punch | mid_side_test_minus20.wav | 0.63 | +2.88 | -0.01 |
| punch | click_track.wav | 8.07 | +11.12 | -1.30 |
| spatial | pink_noise_minus20.wav | 0.10 | -0.00 | +0.00 |
| spatial | pink_noise_minus14.wav | 0.19 | -1.29 | +0.05 |
| spatial | pink_noise_minus10.wav | 0.36 | -4.49 | +0.11 |
| spatial | sine_sweep_minus20.wav | 0.60 | -1.88 | +0.21 |
| spatial | tone_ladder_minus20.wav | 0.60 | -2.07 | -0.98 |
| spatial | dynamic_test_minus14.wav | 0.34 | -2.26 | +0.11 |
| spatial | mid_side_test_minus20.wav | 0.83 | -0.62 | -0.16 |
| spatial | click_track.wav | 7.32 | +18.34 | -2.83 |
| tape | pink_noise_minus20.wav | 0.27 | -0.00 | +0.01 |
| tape | pink_noise_minus14.wav | 0.30 | -1.23 | +0.08 |
| tape | pink_noise_minus10.wav | 0.65 | -4.86 | +0.22 |
| tape | sine_sweep_minus20.wav | 1.00 | -1.11 | +0.36 |
| tape | tone_ladder_minus20.wav | 1.00 | -1.41 | -1.90 |
| tape | dynamic_test_minus14.wav | 0.63 | -3.20 | +0.22 |
| tape | mid_side_test_minus20.wav | 1.36 | +0.18 | -0.25 |
| tape | click_track.wav | 12.90 | +16.55 | -5.02 |
| universal | pink_noise_minus20.wav | 0.12 | +0.00 | +0.01 |
| universal | pink_noise_minus14.wav | 0.13 | -1.40 | +0.02 |
| universal | pink_noise_minus10.wav | 0.17 | -5.58 | +0.01 |
| universal | sine_sweep_minus20.wav | 0.64 | -1.51 | +0.14 |
| universal | tone_ladder_minus20.wav | 0.56 | -1.81 | -0.52 |
| universal | dynamic_test_minus14.wav | 0.16 | -5.50 | +0.01 |
| universal | mid_side_test_minus20.wav | 1.04 | -0.42 | -0.07 |
| universal | click_track.wav | 11.63 | +17.70 | -4.90 |
| warm | pink_noise_minus20.wav | 0.40 | +0.00 | +0.08 |
| warm | pink_noise_minus14.wav | 0.42 | -1.57 | +0.10 |
| warm | pink_noise_minus10.wav | 0.42 | -7.03 | +0.13 |
| warm | sine_sweep_minus20.wav | 0.52 | -2.03 | +0.27 |
| warm | tone_ladder_minus20.wav | 0.49 | -2.39 | -1.34 |
| warm | dynamic_test_minus14.wav | 0.39 | -7.07 | +0.13 |
| warm | mid_side_test_minus20.wav | 0.75 | -0.46 | -0.05 |
| warm | click_track.wav | 17.03 | +18.30 | -5.67 |