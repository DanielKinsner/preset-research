# YES Master vs BandLab — Preset Distinctiveness Head-to-Head

_Both services were fingerprinted with the identical pipeline and neutral protocol
(input gain 0, intensity 0.5 / "Normal"); the YES Master capture is verified three ways
(`reports/validation/yesmaster-capture-verdict.md`). Numbers below are from
`tools/analysis_distinctiveness.py` run on each service's `canonical.json`. YES Master uses
the **loudness-parity** set (each preset at its own natural loudness — apples-to-apples with
how BandLab renders)._

---

## The headline (plain version)

**Your presets are bunched together much tighter than BandLab's.** On the same 28-feature
measurement, the closest any two BandLab presets get is **4.16**. Your closest pair is
**2.47** — and you have **five** pairs that are *closer than BandLab's closest pair ever
gets*. Translation: several of your presets are near-duplicates of each other.

The good news: **`oomph` proves you can do it.** It's a genuinely distinct preset (deep
sub + dark tone), more distinct from its neighbors than anything in BandLab's lineup. The
job is to make a few more presets behave like `oomph` does — stand out — instead of
huddling in the middle.

## The numbers

| | BandLab | YES Master |
|---|---|---|
| Tightest pair (lower = more redundant) | **4.16** (tape~universal) | **2.47** (loud~punch) |
| Pairs below BandLab's 4.16 floor | 0 (by definition) | **5** |
| Genuinely distinct "singleton" presets | 3 (natural, oomph, punch) | **1** (oomph only) |
| Loudness spread (LUFS) | 6.4 | 4.86 |
| Tilt spread (dB/oct) | 1.67 | 0.79 |
| Stereo method & reach | decorrelation — widens any mix (spatial −0.315) | M/S side-scale only — gentle (lineup span ≈0.16), does nothing on narrow mixes |

### Your five near-duplicate pairs (all below BandLab's tightest gap)
1. **`loud` ~ `punch` — 2.47.** Nearly the same preset. They even share an identical
   loudness target (−7.39 LUFS). Stereo difference between them: 0.03 (none).
2. **`spatial` ~ `tape` — 2.56.** They read as twins *on this measure only* — the near-mono
   test signal can't show width (see the stereo correction below). `spatial` (width 1.16)
   genuinely does widen vs `tape` (0.99); on real stereo material they separate more than 2.56.
3. **`spatial` ~ `universal` — 3.16.**
4. **`tape` ~ `universal` — 3.49.**
5. **`custom` ~ `universal` — 3.75.**

`clarity`, `spatial`, `tape`, `universal` collapse into **one 4-preset blob** (internal
distances 2.56–4.39). That's four slots doing roughly one job.

---

## Axis-by-axis: where you use each lever, and where you waste it

**1. Stereo width — real but gentle, and partly a measurement blind spot. (CORRECTION.)**
My first pass read "stereo axis dead" because every preset measured ≈0 correlation change.
That was the *test signal*, not the presets: the only stereo probe (`mid_side_test`) is
near-mono (side ~24 dB down), and YES Master widens by **M/S side-scaling** — scaling a
near-zero side does nothing, so a real 1.16× widener reads −0.006. The presets *do* carry a
sensible width spread (`spatial` 1.16 → `oomph` 0.95). Confirmed **through the real engine**
on a new correlation-0.5 stereo probe (`source/test-signals/stereo_field_minus20.wav`,
measured by `tools/measure_stereo_width.py`): `spatial` widens **−0.091**, `oomph` narrows
**+0.059**, full lineup span **0.150** — and the `trim_width` guardrail is NOT cutting it
(1.16 is substantially applied). Three genuine gaps remain: (a) the reach is gentle
(`spatial` −0.091 vs BandLab `spatial`'s −0.315 reach), (b) side-scaling can't widen
already-narrow/mono material at all, whereas BandLab's decorrelation widens anything, and
(c) a measurement nuance worth knowing — the chain *itself* narrows ~+0.025 (saturation/comp),
mildly working against the width knob.

**2. Tone — too uniform.** Your tilt spans only 0.79 dB/oct (BandLab 1.67), and almost
everything clusters at the bright end with a near-identical "slight sub-cut + slight air
lift." Only `oomph` (−0.57, +sub) has a real tonal identity. The dark end is nearly empty.

**3. Loudness — under-spread and double-booked.** 4.86 LUFS of range vs BandLab's 6.4, and
`loud` + `punch` share the *same* target (−7.39), which is most of why they're your closest
pair. Cheapest separation you can buy: put every preset on its own loudness rung.

**4. Dynamics — your one healthy axis. Keep it.** `loud` (−9.91) → `custom` (−1.51) is a
solid 8.4 dB spread. This is doing real work; lean on it.

---

## Punch-list — prioritized, mapped to your code

Calibration lives in `src-tauri/src/reference_tuning.rs` (per-preset reference targets;
it already computes `stereo_width_gap` and `stereo_correlation_gap`) + `dsp.rs`. Per the
YES Master `CLAUDE.md`, preset calibration is taste-dependent — **audition + capture a
listening note before committing each change** (especially `oomph`, the least-matched).
These are measurement-backed *targets to chase*, not blind edits.

- **P1 — Measure width first, then make `spatial` bolder.** `spatial` is not broken (width
  1.16 already widens ~−0.12 on real stereo), but it's gentle and side-scaling does nothing
  on narrow mixes. Step 1: add a proper non-mono test signal so width is measurable through
  the engine (current battery is blind). Step 2 (taste call): either raise `spatial`'s
  `stereo_width` (e.g. 1.16 → ~1.35–1.5) for a bolder side-scale, and/or add a real
  decorrelation stage so it widens *any* material like BandLab (bigger DSP change, watch
  mono-compatibility). Audition before committing.
- **P1 — Split `loud` vs `punch`.** They share a loudness target and barely differ. Pick
  distinct identities: e.g. `punch` = bright + transient emphasis at a slightly lower rung;
  `loud` = pure max-loudness. Put them on different loudness rungs (≥1.5–2 LUFS apart).
- **P2 — Break up the `clarity`/`tape`/`universal` blob.** Give each a distinct tonal
  corner: `universal` = flat reference (anchor), `clarity` = presence/air lift, `tape` =
  warm, rolled-off highs + saturation character. Right now they're nearly identical.
- **P2 — Populate the dark end.** Only `oomph` is dark. Make `warmth` genuinely warm/dark
  (currently a mild −0.24) so the tonal axis spans both directions.
- **P3 — Consider a mono-narrowing / mono-safe preset.** Positive correlation change is a
  direction no preset in either service uses — instant differentiation + a real delivery
  use-case (club/mono-sum safety).

## How to verify a fix worked

Re-render through the fingerprint runner, re-fingerprint, then:
```
.venv/Scripts/python tools/analysis_distinctiveness.py --service <your-new-set>
```
**Pass condition:** every pairwise distance **> 4.16** (beat BandLab's tightest gap).
Stretch goal: tighten nothing below ~5 and keep `oomph`'s standout character. Also confirm
`spatial` now shows a clearly negative `correlation_change` and `loud`/`punch` no longer
share a loudness rung.

---

### Honest caveats
- Distinctiveness on neutral test signals is a strong *proxy* for perceived distinctiveness
  on music, not identical to it. The **directions** here are robust (stereo is genuinely
  unused; `loud`≈`punch` genuinely overlap), but treat exact distances as indicative.
- n is small (8–9 presets), so single outliers (`oomph`) swing some rankings. That doesn't
  change the core finding: outside `oomph`, your presets need pulling apart.
