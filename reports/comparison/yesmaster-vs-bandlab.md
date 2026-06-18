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
| Presets that move stereo at all | 1 (spatial, −0.315) | **0** |

### Your five near-duplicate pairs (all below BandLab's tightest gap)
1. **`loud` ~ `punch` — 2.47.** Nearly the same preset. They even share an identical
   loudness target (−7.39 LUFS). Stereo difference between them: 0.03 (none).
2. **`spatial` ~ `tape` — 2.56.** `spatial` is supposed to be your *wide* preset but does
   no widening, so it's a twin of `tape`.
3. **`spatial` ~ `universal` — 3.16.**
4. **`tape` ~ `universal` — 3.49.**
5. **`custom` ~ `universal` — 3.75.**

`clarity`, `spatial`, `tape`, `universal` collapse into **one 4-preset blob** (internal
distances 2.56–4.39). That's four slots doing roughly one job.

---

## Axis-by-axis: where you use each lever, and where you waste it

**1. Stereo width — your single biggest wasted axis (highest-leverage fix).**
Every YES Master preset sits at correlation change ≈ 0, *including `spatial`* (−0.006).
BandLab at least uses it once (`spatial` = −0.315, a real widener). Stereo currently
contributes **almost nothing** to telling your presets apart. Turning it on would
single-handedly pull `spatial` out of the blob — and a *narrowing* / mono-safe preset is a
direction **neither** service uses (free territory).

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

- **P1 — Make `spatial` actually widen.** Give it a real negative `stereo_correlation`
  reference target (~−0.30, BandLab's reach). The `stereo_correlation_gap` is an `Option`,
  so it may currently be unset for `spatial`. This is the highest-leverage single change:
  it gives `spatial` an identity and lights up a dead axis.
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
