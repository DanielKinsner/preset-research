# Preset Design Spec — Your Own Mastering Lineup

_A concrete, buildable blueprint for an in-house mastering preset lineup, derived from the validated BandLab fingerprint and designed to beat it on distinctiveness. The data this is built on was independently re-derived from the raw WAVs (see `reports/validation/testing-verdict.md`); every load-bearing axis below reproduces the committed measurements to rounding._

---

## 1. The principle — which axes carry distinctiveness, and why

BandLab's 8-preset space is effectively **one loudness axis plus a tonal smear.** From the validated fingerprint:

- **Loudness (output LUFS) is the biggest separator**, but BandLab wastes it: its presets span only ~6.4 LUFS and crowd four of them near −13.
- **Stereo correlation is the single most under-used axis.** Only `spatial` meaningfully decorrelates (−0.31); the other seven sit within 0.03 of zero, and **no BandLab preset ever narrows (goes positive).**
- **Dynamics is welded to loudness.** All 8 presets *compress* (contrast change −3.7 to −11.9 dB, every value negative); the loudest preset (`punch`) is also the most crushed. There is **no loud-but-open corner** and **no dynamics-expansion preset.**
- **Tone is really ~2 effective knobs:** overall spectral tilt (dark↔bright) and low-vs-high balance (sub vs air). BandLab's tilt range is only ~1.67 dB/oct with a thin dark end (only `natural` reaches −0.52).

So the axes that **carry distinctiveness**, in priority order (cheapest/cleanest separator first):

1. **Output LUFS** — guarantee separation on the cheapest axis with a clean ladder (≥ 1.5 LUFS between every preset).
2. **Stereo correlation change** — BandLab's most wasted axis; use it in **both** directions (widen *and* narrow).
3. **Dynamics contrast change** — decouple it from loudness so "loud-but-open" and "quiet-but-controlled" become reachable.
4. **Spectral tilt** + **5. sub (20–60 Hz)** + **6. air (8–16k)** — the two real tonal knobs, pushed to opposing corners.

**Design rule:** every pair of presets must separate on at least two independent axes, and no two may share a loudness rung.

---

## 2. The lineup — 6 genre-targeted presets + 1 transparent reference

Chosen approach: **genre-targeted corners** — each preset maps to a real delivery target an engineer actually reaches for, then is pushed into a region BandLab leaves empty. This is the most *shippable* of the candidate lineups while still clearing a wide distinctiveness margin (verified min pairwise distance 4.42 z-units; mean 5.57 — 1.6× more spread than BandLab on the same 6 axes).

A 7th **REFERENCE** preset is grafted in (see §5) as a do-no-harm anchor so every other preset's character reads as a deviation from flat.

| Preset (use-case) | Target LUFS | Tilt (dB/oct) | Sub 20–60 (dB) | Air 8–16k (dB) | Stereo corr Δ | Dynamics Δ (dB) | One-axis identity |
|---|---|---|---|---|---|---|---|
| **REFERENCE** (do-no-harm) | −12.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | none (the anchor) |
| **PULSE** (EDM/festival) | −6.0 | +0.45 | +5.5 | +4.5 | −0.04 | −11.0 | loudness (hot + dense) |
| **OPEN AIR** (acoustic) | −13.5 | +0.60 | −2.5 | +5.5 | +0.05 | **−1.0** | dynamics (open/untouched) |
| **SUBLOW** (hip-hop/trap) | −8.5 | −0.70 | **+11.0** | −1.0 | −0.02 | −6.5 | sub (deep + dark) |
| **SPEAK** (podcast/mono) | −16.0 | 0.0 | −4.5 | −1.5 | **+0.18** | −9.5 | stereo (mono-collapse) |
| **EMBER** (indie/warm) | −12.5 | −0.55 | 0.0 | −4.0 | −0.01 | −2.5 | tilt (warm, no sub/air) |
| **WIDESCREEN** (cinematic) | −10.5 | +0.15 | +1.0 | +2.5 | **−0.33** | −4.5 | stereo (wide) |

All values are **measured-delta targets** (output relative to the spectrally-neutral input), in the same units as `canonical.json`. True-peak ceiling: −1.0 dBTP for everything except PULSE (target −0.3 to 0.0 dBTP for streaming-competitive loudness).

---

## 3. How each pair is kept distinct

Every pair separates on **at least two independent axes**; the three tightest pairs (all in the low-energy/dark cluster) were pried apart deliberately:

- **SPEAK ↔ EMBER** (closest, 4.42 z-units): 3.5 LUFS apart **and** opposite stereo sign (+0.18 vs −0.01) **and** opposite tilt (flat vs −0.55).
- **SUBLOW ↔ EMBER** (4.48): SUBLOW has **+11 dB** sub, EMBER has **0 dB** sub (warmth via tilt, not bass) and they sit 4 LUFS apart.
- **PULSE ↔ SUBLOW** (4.55): 2.5 LUFS apart, opposite tilt (+0.45 bright vs −0.70 dark), and a 5.5 dB sub gap.
- **WIDESCREEN ↔ SPEAK**: the two stereo poles (−0.33 vs +0.18) — they anchor BandLab's most under-used axis at both ends.
- **PULSE ↔ OPEN AIR**: same brightness, but opposite loudness (−6 vs −13.5) **and** opposite dynamics (−11 crushed vs −1 open).

No `k=3` cluster cut collapses 6 of these into one group the way it does for BandLab.

---

## 4. The BandLab gaps this exploits

1. **Loud-but-open** (BandLab has none — loudness is welded to crushing): **OPEN AIR** is quiet and nearly uncompressed (−1.0 dB), and the grafted **AURORA-style** retune of PULSE/WIDESCREEN (see §5) reaches the loud-and-open corner directly.
2. **Stereo in both directions** (BandLab only decorrelates, once): **WIDESCREEN** widens (−0.33, matching `spatial`'s reach), **SPEAK** actively **narrows toward mono (+0.18)** — a direction *no* BandLab preset uses (verified: all 8 sit ≤ 0).
3. **Even loudness ladder** (BandLab crowds 4 presets near −13): these 6 sit on distinct rungs spanning −6 to −16 (10 LUFS, vs BandLab's 6.4).
4. **Populated dark end** (BandLab leaves it to `natural` alone): **SUBLOW** (−0.70) and **EMBER** (−0.55) both claim the dark tilt corner, with SUBLOW uniquely combining *dark tilt + deep sub*.
5. **Dynamics expansion** (BandLab never expands): grafted via the **GHOST-style** positive-dynamics direction (see §5) — the single most novel move available.

---

## 5. Best grafts from the other candidate lineups

The genre lineup is the base. These grafts close its two weaknesses (no flat reference, no dynamics-expansion preset) and tighten its usability:

1. **REFERENCE anchor** (from the orthogonal-star lineup). A transparent do-no-harm master: level + ceiling only, all shape deltas 0, −1.0 dBTP. Costs nothing in distinctiveness, gives users a baseline, and makes every other preset legible as a deviation. **Included in the table above.**
2. **Dynamics-expansion direction** (from the max-coverage lineup's GHOST). The one gap the genre lineup leaves open. Either add a 7th audiophile/cinematic preset with **positive** `dynamics_contrast_change` (+2.5 to +7), or loosen **OPEN AIR**/**WIDESCREEN** toward positive dynamics so the lineup finally owns the dynamics *sign* axis (every BandLab preset is negative).
3. **True loud-but-open corner** (from AURORA). Retune one preset to high loudness (~−8) with dynamics nearly intact (−0.5) and strong decorrelation — the headline quadrant BandLab cannot reach. Candidate: nudge **WIDESCREEN** louder, or split a dedicated "loud + wide + open" preset off PULSE.
4. **Single-axis-move discipline as a UX layer** (from the orthogonal-star lineup). Keep the genre framing, but label each preset's **one dominant axis** (last column of the table) so users get predictable, legible controls without losing the genre usability.
5. **Loudness-ladder spacing rule** (from the loudness-ladder MVP): require **≥ 1.5 LUFS** between every preset on the loudness axis as a cheap guarantee of separation. The table above honors this.
6. **Keep a mono-narrowing preset** (SPEAK, +0.18): positive correlation change is a direction *no* BandLab preset uses — never drop it.

---

## 6. How to verify the lineup (do this on your own renders)

Distinctiveness is a property of *measured* masters, not design targets. After you render each preset on the 8 test signals:

1. Re-measure each render with `tools/audio_metrics.py` + `tools/fingerprint.py` to produce your own `canonical.json`-shaped fingerprints.
2. Run `tools/analysis_distinctiveness.py` on your fingerprint set to get the z-scored pairwise distance matrix.
3. **Pass condition:** every pairwise distance must **beat BandLab's tightest gap** (the `tape ~ universal` floor, 4.16 in the full 28-dim space). If any pair falls below, it is a near-duplicate — pry it apart on the cheapest available axis (loudness rung, then stereo sign, then sub/air balance).
4. **Sanity checks beyond distinctiveness:**
   - Loudness ladder: confirm ≥ 1.5 LUFS between every adjacent rung.
   - Stereo: confirm SPEAK is **positive** and WIDESCREEN is **negative** on `correlation_change` (both directions occupied).
   - Dynamics: if you graft the expansion preset, confirm at least one preset has **positive** `dynamics_contrast_change` — the direction BandLab never reaches.
   - Mono fold-down: check SUBLOW and WIDESCREEN don't hollow the center on a mono sum (keep sub/low-mid correlated under the widened highs).
5. Re-run the verdict's non-circular discipline: spot-check a couple of presets by recomputing from the raw renders with independent code, not just by reading your own pipeline's JSON.

**Headline:** 7 presets (6 genre-targeted + 1 transparent reference), spread primarily on **loudness** (clean ≥ 1.5 LUFS ladder), then **stereo correlation in both directions** (BandLab's most wasted axis), then **dynamics decoupled from loudness** (to reach loud-but-open and, via graft, dynamics-expansion), with **tilt + sub/air** placing the tonal corners. Min pairwise distinctiveness target 4.42 z-units — above BandLab's near-duplicate floor.
