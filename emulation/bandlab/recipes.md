# bandlab preset emulation recipes
_Derived from canonical.json. Chain: peak-norm -4.5 dBFS (user-mode) -> EQ shape -> stereo width -> loudness target -> true-peak cap._

**Caveat:** EQ / loudness / stereo are measured and emulable; compression *dynamics* are a target only (no attack/release — the click track can't measure timing). Recipe operating point is pink_-20; see per-preset level dependence.

## clarity
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz +0.5, 60-120 Hz -0.7, 120-250 Hz -2.1, 250-500 Hz -3.2, 500-1k Hz -3.4, 1-2k Hz -3.5, 2-4k Hz -2.1, 4-8k Hz +0.1, 8-16k Hz +0.7
- **Highest bands:** 8-16k Hz +0.7 dB, 20-60 Hz +0.5 dB · **lowest bands:** 1-2k Hz -3.5 dB, 500-1k Hz -3.4 dB
- **Loudness target:** -13.4 LUFS (RMS makeup +7.8 dB @ pink_-20), ceiling +0.22 dBTP
- **Stereo:** correlation change -0.013 (width +4.3 dB)
- **Dynamics target:** crest -1.1 dB, contrast -4.1 dB (approx — no timing)
- **Tonal character:** tilt +0.22 dB/oct, centroid +862 Hz, multiband index 0.264

## natural
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz +0.9, 60-120 Hz +1.3, 120-250 Hz +1.8, 250-500 Hz +0.6, 500-1k Hz +0.6, 1-2k Hz -0.4, 2-4k Hz -1.8, 4-8k Hz -2.2, 8-16k Hz -1.4
- **Highest bands:** 120-250 Hz +1.8 dB, 60-120 Hz +1.3 dB · **lowest bands:** 4-8k Hz -2.2 dB, 2-4k Hz -1.8 dB
- **Loudness target:** -12.3 LUFS (RMS makeup +8.7 dB @ pink_-20), ceiling +0.08 dBTP
- **Stereo:** correlation change -0.003 (width +1.4 dB)
- **Dynamics target:** crest -2.0 dB, contrast -6.9 dB (approx — no timing)
- **Tonal character:** tilt -0.52 dB/oct, centroid -808 Hz, multiband index 0.365

## oomph
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz +9.9, 60-120 Hz +2.3, 120-250 Hz -2.0, 250-500 Hz -4.6, 500-1k Hz -4.0, 1-2k Hz -3.7, 2-4k Hz -2.8, 4-8k Hz +0.1, 8-16k Hz -0.9
- **Highest bands:** 20-60 Hz +9.9 dB, 60-120 Hz +2.3 dB · **lowest bands:** 250-500 Hz -4.6 dB, 500-1k Hz -4.0 dB
- **Loudness target:** -13.0 LUFS (RMS makeup +8.2 dB @ pink_-20), ceiling -0.14 dBTP
- **Stereo:** correlation change -0.006 (width +2.4 dB)
- **Dynamics target:** crest -1.6 dB, contrast -8.3 dB (approx — no timing)
- **Tonal character:** tilt -0.24 dB/oct, centroid -2027 Hz, multiband index 0.315

## punch
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz -0.7, 60-120 Hz -2.7, 120-250 Hz -5.8, 250-500 Hz -7.7, 500-1k Hz -6.9, 1-2k Hz -4.1, 2-4k Hz -0.9, 4-8k Hz +2.5, 8-16k Hz +3.7
- **Highest bands:** 8-16k Hz +3.7 dB, 4-8k Hz +2.5 dB · **lowest bands:** 250-500 Hz -7.7 dB, 500-1k Hz -6.9 dB
- **Loudness target:** -7.4 LUFS (RMS makeup +12.1 dB @ pink_-20), ceiling +1.11 dBTP
- **Stereo:** correlation change -0.124 (width +12.7 dB)
- **Dynamics target:** crest -6.6 dB, contrast -11.9 dB (approx — no timing)
- **Tonal character:** tilt +1.15 dB/oct, centroid +3614 Hz, multiband index 1.01

## spatial
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz -0.3, 60-120 Hz -0.3, 120-250 Hz -0.3, 250-500 Hz -0.2, 500-1k Hz -0.3, 1-2k Hz -0.5, 2-4k Hz -0.4, 4-8k Hz +1.3, 8-16k Hz +2.4
- **Highest bands:** 8-16k Hz +2.4 dB, 4-8k Hz +1.3 dB · **lowest bands:** 1-2k Hz -0.5 dB, 2-4k Hz -0.4 dB
- **Loudness target:** -10.3 LUFS (RMS makeup +8.9 dB @ pink_-20), ceiling +1.20 dBTP
- **Stereo:** correlation change -0.315 (width +16.8 dB)
- **Dynamics target:** crest -2.0 dB, contrast -6.3 dB (approx — no timing)
- **Tonal character:** tilt +0.30 dB/oct, centroid +1219 Hz, multiband index 0.209

## tape
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz -0.4, 60-120 Hz +0.1, 120-250 Hz +0.7, 250-500 Hz +1.1, 500-1k Hz +0.8, 1-2k Hz -0.4, 2-4k Hz -2.3, 4-8k Hz +1.2, 8-16k Hz +3.9
- **Highest bands:** 8-16k Hz +3.9 dB, 4-8k Hz +1.2 dB · **lowest bands:** 2-4k Hz -2.3 dB, 1-2k Hz -0.4 dB
- **Loudness target:** -10.7 LUFS (RMS makeup +8.2 dB @ pink_-20), ceiling -0.95 dBTP
- **Stereo:** correlation change -0.028 (width +6.6 dB)
- **Dynamics target:** crest -2.4 dB, contrast -5.4 dB (approx — no timing)
- **Tonal character:** tilt +0.21 dB/oct, centroid +1752 Hz, multiband index 0.35

## universal
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz +0.2, 60-120 Hz +0.1, 120-250 Hz -0.3, 250-500 Hz -1.2, 500-1k Hz -1.0, 1-2k Hz -0.5, 2-4k Hz -1.3, 4-8k Hz -0.1, 8-16k Hz +0.6
- **Highest bands:** 8-16k Hz +0.6 dB, 20-60 Hz +0.2 dB · **lowest bands:** 2-4k Hz -1.3 dB, 250-500 Hz -1.2 dB
- **Loudness target:** -11.6 LUFS (RMS makeup +9.1 dB @ pink_-20), ceiling +0.61 dBTP
- **Stereo:** correlation change -0.008 (width +3.1 dB)
- **Dynamics target:** crest -2.2 dB, contrast -6.1 dB (approx — no timing)
- **Tonal character:** tilt +0.03 dB/oct, centroid +258 Hz, multiband index 0.13

## warm
- **Tonal EQ shape (dB, makeup-removed):** 20-60 Hz -0.9, 60-120 Hz +4.7, 120-250 Hz +3.9, 250-500 Hz +3.3, 500-1k Hz +3.1, 1-2k Hz +2.9, 2-4k Hz +2.9, 4-8k Hz +3.8, 8-16k Hz +4.6
- **Highest bands:** 60-120 Hz +4.7 dB, 8-16k Hz +4.6 dB · **lowest bands:** 20-60 Hz -0.9 dB, 1-2k Hz +2.9 dB
- **Loudness target:** -13.8 LUFS (RMS makeup +3.0 dB @ pink_-20), ceiling -3.63 dBTP
- **Stereo:** correlation change -0.008 (width +3.0 dB)
- **Dynamics target:** crest -0.1 dB, contrast -3.7 dB (approx — no timing)
- **Tonal character:** tilt -0.01 dB/oct, centroid +743 Hz, multiband index 0.192
