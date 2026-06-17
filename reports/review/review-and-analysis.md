# Preset-Research Measurement Instrument — Review & Analysis

_Generated 2026-06-16. Review-only: no source files were modified. All findings below were independently verified by reading `tools/` in full and reproducing the numbers against the committed data; the two analyses were run with the repo venv. Severities use P0 (ship-blocker) → P3 (polish)._

---

## 1. Executive Summary

The instrument is **fundamentally sound and trustworthy for its core job** — the input→output delta methodology, the per-preset EQ/loudness/dynamics/stereo fingerprints, and the headline DSP conclusions are correct. The project's strongest claim (BandLab is a peak-normalizer to **-4.5 dBFS**, confirmed on all 8 signals to within 0.05 dB) is verified, and the methodology's main limitation (dual-normalizer chain measured at gain 0) is honestly disclosed by the authors themselves.

**There are no P0 ship-blockers.** The defects are bounded and, in almost every case, do **not** corrupt the currently-committed numbers — they are either (a) latent traps that fire only on inputs BandLab does not currently produce, or (b) interpretation/presentation/documentation defects in the report layer and the prose docs.

Verified-finding counts: **P0 = 0, P1 = 2, P2 = 7, P3 = 13.**

Two findings deserve action before the numbers are quoted externally:

- **P1 — True-peak over-reports by ~+1 dB at file boundaries** (`audio_metrics.py`). A phantom inter-sample peak from `resample_poly` edge ringing. Feeds a hard clip/no-clip verdict thresholded at exactly 0.0 dBTP, so it can flip the judgement.
- **P1 — The loudness chart plots bar length inversely to loudness** (`compare.py`). The loudest preset gets the shortest bar; a reader scanning the headline chart reads the loudness ranking backwards.

Everything else is P2/P3: HF-biased spectral tilt, a few mislabeled/over-stated interpretation lines, docstring claims that are quantitatively false, and latent edge-case fragility (click detection, tone-ladder rep dedup, onset alignment, chart KeyErrors).

The two analyses answer the operator's strategic questions cleanly: **the EQ is static (content-independent)** and **BandLab's presets are only moderately distinct** (6 of 8 collapse into one loose cluster).

---

## 2. Verified Review Findings (ranked P0 → P3)

> P0: none.

### P1 — true_peak_dbtp over-reports by ~1 dB from resample_poly edge transients (phantom inter-sample peaks)

- **File:** `tools/audio_metrics.py`
- **Location:** `true_peak_dbtp()`, lines 102–112 (`signal.resample_poly(data[:, ch], oversample, 1)`)
- **Problem:** `scipy.signal.resample_poly` filters against implicit zero-padding at both array ends, so the polyphase FIR rings at the file boundaries and injects a phantom overshoot unrelated to any real inter-sample peak. Reproduced exactly: a constant DC signal of amplitude 0.8 (true peak -1.938 dBFS, by definition **zero** inter-sample content) reports `true_peak_dbtp = -0.851 dBTP` — a **+1.087 dB phantom**, with the upsampled max (0.9066) localized to the first/last samples while the interior is exactly 0.8005. A hard step 0→0.9 reports +0.17 dBTP from Gibbs ringing. Any master whose first or last sample is non-zero and near full scale (abrupt start/end, fade-less cut, DC offset) will have its true-peak inflated.
- **Why it matters:** This is the exact number `fingerprint.json` exposes as `true_peak_ceiling_dbtp` / `output_true_peak_dbtp` and the input→output true-peak delta. Critically, `compare.py:274` makes a hard clip verdict — `clippers = [n for n in L if L[n]['true_peak_ceiling_dbtp'] > 0.0]` — thresholded at **exactly 0.0 dBTP**, precisely where a spurious ~+1 dB boundary inflation can flip a no-clip into a clip and corrupt the per-preset limiter ceiling that informs DSP limiter decisions.
- **Fix:** Trim the resampler transient before taking the max (discard ~half the FIR length, e.g. `up2[trim:-trim]` with `trim ≈ 16*oversample`) — verified to recover -1.933 dBFS (≈ true -1.938). Note: padding with zeros does **not** cure a sustained/DC edge (it just relocates the same step inward and it still rings); use the trim, or edge-reflect carefully. 4x oversampling is otherwise acceptable for the project's purposes once the edge transient is removed.

### P1 — Output-loudness bar lengths are inversely proportional to loudness

- **File:** `tools/compare.py`
- **Location:** `chart_loudness_grid` → `_hbar`, line 99: `_hbar(axes[0,0], names, lufs, "Output loudness (louder = up)", "LUFS")`
- **Problem:** The top-left panel plots absolute `output_integrated_lufs`, which are all negative (punch -7.39 … warm -13.77). `matplotlib.barh` draws every bar from x=0 leftward, so bar **length** equals |LUFS| = distance below full scale. The loudest preset (punch) gets the **shortest** bar; the quietest (warm) gets the **longest**. Vertical ordering is correct (loudest on top, per the "louder = up" title), but the dominant visual cue (bar length) encodes the exact **opposite** of loudness. This is the only `_hbar` panel affected — every other panel plots a delta centered near 0, where length-from-0 is meaningful.
- **Why it matters:** Loudest/quietest is the report's headline DSP conclusion (first finding line and the printed `Loudest=/Quietest=`). A chart that visually inverts it can steer a reader to the wrong preset. (Mitigation already present: the correct numeric value is printed as a text label on each bar and in the table.)
- **Fix:** Don't plot absolute LUFS as a bar from 0. Plot loudness relative to the group max (`LUFS - max(LUFS)`, so 0 = loudest), or set a sensible left x-limit and draw deviation from a floor, or switch this single panel to a dot/lollipop plot where **position** carries the meaning. Apply the same care to any future absolute-magnitude (non-delta) quantity routed through `_hbar`.

### P2 — band_energy_dbfs docstring "summing band powers recovers the broadband RMS" is false for the actual stereo signals

- **File:** `tools/audio_metrics.py`
- **Location:** `band_energy_dbfs()` docstring, lines 143–147; via `_mono()` lines 67–69
- **Problem:** `band_energy_dbfs` computes the PSD of the **mono** downmix (`_mono()` = mean of channels), while `rms_dbfs` is computed over all per-sample data across **both** channels. On the real committed `pink_noise_minus20` record, `rms_dbfs = -21.0` but the sum of linear band powers = **-27.4 dBFS** — a **6.4 dB** discrepancy. Decomposed: ~2.86 dB from the mean-downmix discarding the decorrelated side energy (pink correlation ~0.035) and ~3.51 dB from the bands spanning only 20 Hz–16 kHz while Nyquist is 22.05 kHz. The docstring's promised identity is simply false for these files.
- **Why it matters:** A scientific instrument whose docstring promises a recoverable relationship that is off by 6 dB will mislead anyone interpreting absolute band levels. (The per-band **deltas** in fingerprinting are unaffected — input and output both pass the identical mono downmix, so the offset cancels — so this is a correctness-of-claim/interpretability bug, not a delta-corrupting one.)
- **Fix:** Correct the docstring to state band powers sum to the **mono-downmix** mean-square over the 20 Hz–16 kHz range, not full-file stereo RMS; or compute per-channel PSD and average band powers (preserving uncorrelated energy) and extend coverage. State explicitly that absolute band dBFS are mono-downmix levels and only the deltas are makeup-gain-comparable.

### P2 — Spectral slope is dominated by HF bins (linear PSD, unweighted log-frequency OLS)

- **File:** `tools/audio_metrics.py`
- **Location:** `spectral_slope_db_per_oct()`, lines 159–171 (`np.polyfit` on `logf` vs `ydb` over linearly-spaced Welch bins)
- **Problem:** The fit regresses PSD(dB) against log10(f) using Welch bins that are **linearly** spaced in Hz, so bin count doubles every octave; the top ~1.3 octaves alone carry ~17% of the leverage. OLS therefore weights HF ~5–6x more per dB than LF. Verified on synthetic pink: a +6 dB low-shelf @250 Hz moves slope by only **-0.24 dB/oct**, an equal +6 dB high-shelf @4 kHz moves it **+1.48 dB/oct** — a ~6x asymmetry that is a bin-density artifact, not signal physics (re-binning to 1/3-octave collapses it to ~0.8x). The centroid metric responds correctly to the same low-shelf (-1417 Hz), exposing the discrepancy.
- **Why it matters:** `spectral_tilt_change_db_per_oct` and `multiband_density_index` are headline tonal-tilt fingerprints feeding the "brightest/darkest" rankings. A "warm" preset working mainly below 500 Hz looks spectrally near-neutral by this number, understating its bass move ~6x relative to an equal treble move. (Ideal pink still reads ~-3.01, so the bias is invisible in the validation pass.)
- **Fix:** Make the regression log-frequency uniform — bin the PSD into log-spaced (1/3-octave) points and fit those, or apply 1/f weighting in a weighted least squares. Cross-check against the centroid metric, which already handles LF moves correctly.

### P2 — Click detection and per-impulse width use a single global-max threshold

- **File:** `tools/audio_metrics.py`
- **Location:** `analyze_click_track()`, lines 254–283 (`thr = max(env)*thresh_ratio`; groups; `widths = grp[-1]-grp[0]+1`)
- **Problem:** Detection threshold is `thresh_ratio` (0.3) of the **global** peak envelope, so any click below 0.3x the loudest is never detected. Reproduced: a 120-click track with alternate clicks 20 dB down reports `n_impulses = 60` (half missed), which would also spuriously fail the `n_impulses == 120` validation gate (`validate_signals.py:107`, a hard `check_equal`). Separately, `mean_width_samples` is the span exceeding the global threshold, so "width" is a function of the chosen ratio and the loudest click, not a physical impulse width.
- **Why it matters:** `n_impulses` is a validation gate and the click track exists to capture limiter transient reshaping; a detector that drops attenuated clicks under-counts exactly when a preset is doing the most to the transients. (The current uniform-level source passes, so this is latent fragility. Note: the downstream `click_attack_release` limiter-timing metric uses period gating, not this detector, so its medians are robust.)
- **Fix:** Detect against an absolute or locally-adaptive threshold (moving-median + k·MAD, or expected-period gating since the 0.5 s grid is known). Report width at a per-impulse relative level (e.g. -6 dB from each impulse's own peak), documented as a relative-threshold envelope width.

### P2 — "Loudness chase" label conflates fixed-gain processing with adaptive loudness-targeting

- **File:** `tools/fingerprint.py` (and `tools/compare.py`)
- **Location:** `aggregate_preset`, level_dependence block lines 223–231 + note; `compare.py` `chart_level_dependence`/`_level_slope`/`hardest_chase` lines 122–145, 278–311
- **Problem:** The metric labels a **falling** loudness-lift slope (`output_lufs - input_lufs` across -20/-14/-10 pink) as "adaptive loudness-targeting / loudness chase." But lift = out − in falls with input level even for a pure fixed-gain chain (input rises while a constant gain holds output). The true signature of loudness-targeting is **flat output LUFS** across input levels. The data contradicts the label: warm's output LUFS spans ~6.85 dB and natural ~4.91 dB — these chains are clearly **not** converging on a fixed target, yet warm/punch surface as the "hardest loudness chase."
- **Why it matters:** This is the client/agent-facing interpretation of adaptivity feeding DSP decisions; it can mislabel non-adaptive behavior as adaptive. The underlying lift numbers are correct — the derived interpretation is the problem. (Note: one sub-claim in the finding's reasoning — that observed slopes are "less steep than -10 LU fixed gain, the opposite of pulling back" — is inverted; fixed gain is slope 0, perfect targeting is -10, and the observed -7.45/-3.15 lie between, i.e. partial pull-back in the expected direction. This weakens only that paragraph, not the core defect.)
- **Fix:** Report adaptivity from **output-LUFS spread/flatness** across input levels (`max-min`; small ⇒ targeting), or compare the lift slope against the fixed-gain expectation and flag "pulls back" only when steeper than fixed gain. Add `output_integrated_lufs_by_input_level` alongside the two lift series so flatness can be read, and update the note + `hardest_chase` wording.

### P2 — Tone-gain overlay billed as "cross-validation" but the two charts use incompatible y-normalizations

- **File:** `tools/compare.py`
- **Location:** `chart_tone_gain` (lines 148–171, title 169) and section blurb (lines 362–363), vs `chart_eq_overlay` (lines 56–72)
- **Problem:** The EQ contour chart plots `eq_contour_db`, which is mean-centered (curves sit symmetrically around 0, ~-6..+10). The tone-gain chart plots `tone_gain_db` = **absolute** per-frequency gain (output − input), **not** mean-centered, floating at roughly +5..+15 dB (it still contains the broadband makeup gain). So the same preset appears around 0 in one chart and around +7 in the other. A reader invited to "cross-validate" by eye sees curves at completely different vertical offsets and could wrongly conclude the cross-check fails — when only the constant makeup offset differs and the shapes actually agree (mean-centering the tone-gain collapses it onto the contour).
- **Why it matters:** Cross-validating the EQ measurement is the chart's entire purpose, and that measurement drives tonal DSP decisions. The validation framing is sound; the rendering defeats it.
- **Fix:** Mean-center the tone-gain curve before plotting (subtract each preset's own mean tone gain) to match the `eq_contour_db` convention. Alternatively overlay both on one axis, or at minimum amend the blurb to say "compare shape, not absolute level."

### P2 — "Widest stereo" headline uses the dB width metric the report's own blurb labels untrustworthy

- **File:** `tools/compare.py`
- **Location:** `widest = max(wid, key=wid.get)` line 289 and finding lines 315–317 (uses `stereo.width_change_db`); `chart_stereo` left panel line 196; vs section blurb lines 372–375
- **Problem:** The section text explicitly disclaims `width_change_db` ("width in dB sits on a near-mono floor … so it can swing more dramatically than the perceptual change") and names `correlation_change` as the trustworthy metric. Yet the "Widest stereo" headline is computed from `width_change_db`, and the stereo figure places the disclaimed dB panel on the **left** (read first). spatial reads +16.8 dB and punch +12.7 dB — exactly the numbers the blurb warns are inflated by the near-mono floor.
- **Why it matters:** A stereo-width ranking informs spatial-processing DSP choices; the most prominent number contradicts the report's own stated trust hierarchy and overstates perceptual width. (Caveat that keeps this at P2: the dB and correlation rankings are nearly identical — Spearman 0.994 — so the **which-preset** conclusion does not actually flip; spatial wins under both. The defect is the inflated magnitude and the trust-hierarchy contradiction, not a wrong winner.)
- **Fix:** Base the headline on `correlation_change` (or report both, leading with correlation). Reorder `chart_stereo` so the correlation panel is on the left, or annotate the dB panel as "amplified by near-mono input floor; see correlation panel." Keep the dB number but demote its prominence.

### P2 — "Only warm is genuinely non-monotonic in LUFS" is contradicted by clarity in the same data

- **File:** `STATUS.md` (duplicated in `HANDOFF.md`)
- **Location:** `STATUS.md` line ~87/89; `HANDOFF.md` line ~133
- **Problem:** The claim is that warm is the **only** preset non-monotonic in LUFS loudness lift. But clarity's `loudness_lift_lufs_by_input_level` is 6.972 (-20) → 2.568 (-14) → 2.908 (-10): it dips at -14 then rises at -10 — the exact same non-monotonic signature attributed uniquely to warm (6.621 → 2.225 → 3.471). By the document's own criterion (a dip at -14 below both neighbors), clarity qualifies too. The magnitudes differ (warm rebound +1.25 LU, clarity +0.34 LU), so warm's is stronger, but the word "only" is factually wrong. The other six presets are strictly monotonic.
- **Why it matters:** Non-monotonicity is cited as evidence of a specific adaptive behavior; an exclusivity claim the data refutes weakens the narrative and is exactly what a reader cross-checking the JSON catches immediately. (No DSP computation is affected — narrative accuracy only.)
- **Fix:** Reword to "warm and clarity are non-monotonic in LUFS (warm strongly, +1.25 LU rebound; clarity mildly, +0.34 LU); all others strictly monotonic-decreasing," or add and state a magnitude threshold. Do not claim "only warm."

### P2 — "Brightest = punch +2.18 dB/oct" single-number tilt is HF-weighted and overstates uniform brightening for U-shaped presets

- **File:** `measurements/fingerprints/bandlab/canonical.json` (metric in `tools/audio_metrics.py`)
- **Location:** `spectral_tilt_change_db_per_oct` (punch 2.182); `spectral_slope_db_per_oct` lines 159–171
- **Problem:** Same HF bin-density bias as the slope finding above. punch's actual tonal curve (`eq_contour`) is a deep mid-scoop with HF lift: +1.8 (20–60) / -5.2 (250–500) / +6.2 (8–16k). Fitting a single tilt to that yields +2.18, dominated by the HF rise; a tilt fit to the octave-uniform 9-band `eq_contour` gives only **+0.73 dB/oct**. So "punch is the brightest preset" conflates "lifts the top end" with "uniformly brighter," when punch actually scoops the mids hard. The project already handles this exact failure for oomph (reports tilt AND centroid, "disagree by design") but states punch's brightness without the caveat — and punch's centroid (+3614 Hz) happens to agree, masking that the tilt number itself is HF-biased.
- **Why it matters:** These tilt numbers are headline brightest/darkest rankings informing DSP/EQ decisions. An HF-biased slope on a non-straight curve misleads anyone emulating the preset's actual tonal balance.
- **Fix:** Either add the oomph-style "report tilt + centroid + note the curve shape" caveat to punch (its brightness is HF-lift-over-mid-scoop, not a uniform tilt), or compute the tilt on the 9-band `eq_contour` (octave-uniform weighting). Document which slope definition the headline "dB/oct" refers to.

### P3 — loudness_range NaN is swallowed by a bare except, hiding genuine pyloudnorm failures

- **File:** `tools/audio_metrics.py`
- **Location:** `loudness_metrics()`, lines 120–128 (`try: lra = ...; except Exception: lra = nan`)
- **Problem:** `loudness_range` legitimately raises/degenerates on short or steady material (pyloudnorm raises a plain `ValueError` on sub-block-size audio). The bare `except Exception` converts **any** failure — a real bug, a wrong sample rate, a future API change — into a silent NaN with no logging, propagating as `lra_change_lu = None` through the fingerprints. For the 60 s signals this currently works, but the silent-swallow makes regressions invisible.
- **Why it matters:** A silently NaN'd loudness-range that should have been a number (or a real crash) undermines trust in the LRA/dynamics fingerprint and masks future library/input regressions.
- **Fix:** Catch the specific exception class (or check the duration/precondition explicitly) and record a diagnostic (exception type / warning) instead of a bare NaN. At minimum narrow `except Exception`.

### P3 — Pooled RMS across all channels is a non-obvious convention vs the documented full-scale-sine reference

- **File:** `tools/audio_metrics.py`
- **Location:** `rms_dbfs()`, lines 98–99 (mean-square over the whole 2-D array)
- **Problem:** `rms_dbfs` energy-pools across all channels. For an asymmetric stereo file this reads ~3 dB below the louder channel (L=0.5 const, R=0 → peak -6.02 dBFS but pooled rms -9.03 dBFS). The module docstring anchors the convention to "full-scale sine reads -3.01 dBFS RMS," true for mono/correlated stereo, but a user comparing a single channel's level to the reported number is off by up to 3 dB for asymmetric content. (On the repo's near-symmetric signals the pooled-vs-per-channel gap is ~0.01 dB, so the discrepancy never bites in practice — this is a documentation/convention gap, not a correctness bug.)
- **Why it matters:** Surfacing the convention prevents 3 dB level-comparison errors when someone reads `rms_dbfs` as "the channel level."
- **Fix:** Document that `rms_dbfs` is energy-pooled across channels. If a per-channel or max-channel RMS is ever wanted for level comparisons, expose it separately.

### P3 — tone_gains silently drops the first ladder repetition (dict keyed by duplicated expected_hz)

- **File:** `tools/fingerprint.py`
- **Location:** `tone_gains`, lines 69–75
- **Problem:** The tone ladder repeats twice (reps=2), so each frequency's `expected_hz` appears at two segment indices. `tone_gains` builds dicts keyed by `expected_hz`, so the second occurrence **overwrites** the first — only the last rep survives. Verified: 20 input segments collapse to 10 keys; half the measurements are discarded rather than averaged. In current data the two reps agree within 0.001 dB so the result is coincidentally fine, but any time-varying processing (the whole point of reps) would be invisible.
- **Why it matters:** Defeats the redundancy the 2x repetition was designed to provide and would mask drift between passes; per-frequency gain cross-validates the pink EQ contour, so a silently-halved sample set undermines that check.
- **Fix:** Group levels by `expected_hz` across both reps and average (or median) before differencing.

### P3 — band_energy_dbfs docstring "summing band powers recovers broadband RMS" is false (bands miss out-of-range energy)

- **File:** `tools/audio_metrics.py`
- **Location:** `band_energy_dbfs` docstring (lines 144–147); relied on conceptually by `fingerprint.band_deltas` eq_shape normalization
- **Problem:** A second view of the band-sum/RMS gap, here on `pink_noise_minus10`: summed band power -17.2 dBFS vs measured RMS -11.0 dBFS — a 6.2 dB gap (roughly half mono-vs-stereo mismatch, half genuine out-of-band energy below 20 Hz and 16–22.05 kHz). The `eq_shape` normalization (`raw_band - rms_delta`) is still internally consistent arithmetic, but its stated premise ("0 = band moved exactly with overall level") only holds if the RMS delta equals the energy-weighted in-band mean delta, which it need not when out-of-band energy changes. `eq_contour` (`raw - mean(raw)`) is the cleaner mean-centered curve and is unaffected.
- **Why it matters:** A load-bearing docstring asserting an identity off by 6 dB invites future code to trust band-sum == RMS and slightly biases the "makeup-gain-removed" interpretation of `eq_shape` vs the better-behaved `eq_contour`.
- **Fix:** Correct the docstring to state the bands are a partial (20 Hz–16 kHz) decomposition that does **not** sum to full-band RMS. Document `eq_shape`'s zero-reference as the broadband RMS delta, or normalize by the in-band energy-weighted mean. Prefer `eq_contour` for tonal-shape reporting.

### P3 — Tone-ladder segmentation can emit a spurious 21st segment under a long tail

- **File:** `tools/audio_metrics.py`
- **Location:** `analyze_tone_ladder`, lines 235–251 (`n_seg = (len-onset)//seg`, `schedule = (...)[:n_seg]`, `level_spread_db = max-min`)
- **Problem:** `n_seg` is unguarded; a tail pushing usable length past 63 s yields `n_seg = 21` while `schedule` has length 20, so the 21st segment has `expected_hz = None` yet still gets a measured level that feeds `level_spread_db` and the tone count. If that trailing segment is partial/decaying it depresses `min(levels)` and inflates the spread. Current BandLab tails (≤0.42 s) keep this safe. (The validator's per-frequency loop guards on `if t["expected_hz"]:`, so no spurious freq failure — the harm is via `level_spread_db`.)
- **Why it matters:** Defensive — keeps `level_spread_db` and the validator robust if a service ever appends a longer tail or trailing artifact.
- **Fix:** Cap `n_seg` at `min((len-onset)//seg, len(schedule))`, and/or skip tones whose `expected_hz` is None when computing `level_spread_db`.

### P3 — content_onset uses a fixed -50 dBFS / 10 ms gate that can mis-trigger and shift all segments at once

- **File:** `tools/audio_metrics.py`
- **Location:** `content_onset`, lines 72–88
- **Problem:** A 10 ms window at 44.1 kHz = 441 samples = 0.4 cycles of a 40 Hz tone; a sub-threshold LF lead-in, a fade-in, or a quiet pre-roll click can be missed (late onset) or false-trigger (early onset). Because the result is a single integer multiplied into every segment start, a wrong onset shifts **all 20 tone segments** together, corrupting every per-frequency gain at once. The function returns silently with no confidence/quality indicator. Verified: phase-dependent windowed RMS of a near-threshold 40 Hz tone ranges 0.875–1.111x the gate, demonstrating the mis-trigger; it returns 0 for clean cases (so current data is fine).
- **Why it matters:** A silent single-integer mis-alignment is the highest-leverage failure mode in the pipeline — it shifts an entire signal's segmentation — and without a confidence flag it is invisible.
- **Fix:** Cross-check the detected onset against the input, emit an `onset_confidence` / quality flag (RMS margin above threshold), use a first-sustained-frame / hysteresis rule instead of the first single frame, and surface `onset_sec` prominently.

### P3 — Level-dependence x-axis labeled "nominal RMS" while -14/-10 inputs are near/at full scale on peaks

- **File:** `tools/compare.py`
- **Location:** `chart_level_dependence` x-axis label line 140; xticks line 143
- **Problem:** The three pink inputs measure RMS -21.0/-15.0/-11.0 (near the nominal labels, fine), but input **peak** is -6.96 / -0.61 / 0.00 dBFS. The -10 input peaks at full scale and -14 at -0.6 dBFS. The steep loudness-lift drop the chart attributes to "adaptive loudness chase" occurs largely between -20 and -14, exactly where the input transitions from comfortable headroom to peak-limited — so part of the apparent "chase" could be the input running out of peak headroom, not the preset's adaptive gain. (Output peak is strikingly stable per preset, so the chain IS limiting — the interpretation is fundamentally sound; this is an unstated confound.)
- **Why it matters:** Keeps the "chase" interpretation honest about a confound the authors disclose elsewhere (RMS vs LUFS) but omit here.
- **Fix:** Add a note (blurb or axis annotation) that the -14 and -10 inputs peak near/at 0 dBFS, so part of the lift reduction at hotter input is headroom-limited, not purely adaptive. Optionally annotate input peak per point.

### P3 — Long/edge bar value-labels collide with the axis and category names in _hbar

- **File:** `tools/compare.py`
- **Location:** `_hbar` text placement lines 87–89 (`ha='left' if v>=0 else 'right'`)
- **Problem:** For the longest negative bars the value label is right-aligned at the bar tip, landing on/past the left plot edge and overprinting the y-tick name. Rendered output shows fused labels: `warm-13.8` and `warm-3.6` in the loudness grid, `spatial0.315` in the stereo correlation panel, `oomph-3.82` in the click panel. A fused label can flip a sign read (`spatial0.315` reads as +0.315 instead of -0.315) — and the stereo correlation sign distinguishes decorrelated/wider from narrowed, so a swallowed minus is a real readout-integrity defect.
- **Why it matters:** Cosmetic but on a scientific report; a swallowed sign mis-reads a measurement.
- **Fix:** Pad x-limits (`ax.margins(x=0.15)` or explicit `set_xlim` with headroom), place labels inside the bar for extreme values, or always offset the text by a fixed pixel pad. Ensure the minus sign is never swallowed.

### P3 — Loudness/tilt charts index keys directly (no .get), gated only on has_eq presence anywhere

- **File:** `tools/compare.py`
- **Location:** `chart_loudness_grid` lines 94–97 and `chart_tilt` line 109; gate at lines 249–251 uses `has_eq = any(...)`
- **Problem:** `has_eq` is true if **any** preset has `eq_contour_db`. The loudness grid and tilt chart then iterate **all** presets and index `loudness` / `spectral_tilt_change_db_per_oct` directly. `fingerprint.py` only writes these keys inside the `if pink:` block. A preset captured with non-pink signals but no pink reference would lack them, causing a `KeyError` that aborts the whole report rather than gracefully omitting that preset. All 8 current presets have pink, so this is latent. It contradicts the module's stated graceful-absence design ("sections appear only for dimensions the present signals support").
- **Why it matters:** A crash on a partial future capture, inconsistent with the file's scales-automatically contract.
- **Fix:** Filter the name list to presets that actually have the `loudness`/`tilt` keys (mirror the `.get()`-guarded pattern already used for dynamics/stereo/click/level), or skip presets missing `loudness`.

### P3 (verification pass) — The -4.5 dBFS peak-normalizer model is fully verified and the project's strongest claim

- **File:** `competitors/bandlab/capture.json`
- **Location:** `auto_input_gain_finding` + `per_signal` (all 8 signals)
- **Status:** **Not a defect.** The headline "suggested = -4.5 − input_peak_dbfs, confirmed on all 8 signals, max error 0.05 dB" holds exactly. Recomputed `-4.5 - peak` for every signal: max |suggested − model| = 0.050 dB; implied target peaks span -4.45 to -4.55 dBFS. Re-measured the source WAVs with `audio_metrics.peak_dbfs` — `capture.json` input peaks match real measured peaks to within 0.004 dB, so the model is grounded in measurement, not hand-entered. The click_track acid test (peak -0.45 → suggested -4.1) genuinely discriminates a peak target from a loudness target (which would need ~+30 dB). The sample-peak interpretation is confirmed over a true-peak alternative.
- **Action:** None. This is the load-bearing input-stage model for any emulation recipe, and it is correct.

### P3 (verification pass) — Core methodology is sound and its main limitation is honestly disclosed

- **File:** `HANDOFF.md` (section 5b) / `README.md` thesis
- **Status:** **Verification pass.** The thesis "input is neutral, so the output delta IS the preset" is valid for cross-preset comparison — all 8 presets receive the identical neutral input with the input normalizer bypassed (gain 0), so every cross-preset difference is genuinely the preset. The dual-normalizer concern (BandLab peak-conditions input AND drives output to a loudness target, so the delta is the chain's raw level-dependent response, not a typical user's result) is **not hidden** — HANDOFF §5b states it explicitly, flags -10 pink at gain 0 as an off-design over-hot stress test, and prescribes "gain-to-4.5 or interpolate -20/-14." The makeup-gain-RMS-not-LUFS trap is documented inline and both metrics stored. The EQ-shape isolation math is correct (self-test recovers an injected +8 dB + HF shelf).
- **Residual nuance (the one actionable gap):** Because the output is loudness-targeted and limited, the `eq_shape` delta on heavily-limited presets (punch, crest change -6.6) still contains **limiter-induced spectral reshaping** — `eq_shape` removes broadband makeup but not frequency-dependent limiting. This is implicitly acknowledged via the multiband-density index but not called out as a caveat on the `eq_shape` numbers themselves.
- **Fix:** Add one sentence to the EQ-shape methodology note: on heavily-limited presets the makeup-removed `eq_shape` is the chain's net tonal output, not isolated pre-limiter EQ — relevant when building a per-preset emulation recipe that separates EQ from the limiter stage.

### P3 (other docs/methodology notes verified)

- **Docs claim the dynamic analyzer aligns to content onset; the code does not** (`STATUS.md` line 34 / `HANDOFF.md`). `analyze_tone_ladder` calls `content_onset`; `analyze_dynamic` (lines 286–311) windows fixed 5 s segments from t=0 with no onset detection. Impact on committed numbers is nil (BandLab's extra length is a trailing tail, `content_onset` returns 0, contrast identical to 3 decimals across all 8 presets), but the doc claim is false and would silently corrupt results if a service ever prepends leading silence to the dynamic test. **Fix:** add the `content_onset` call to `analyze_dynamic`, or correct the docs.
- **Tone-ladder vs pink cross-validation r values rest on an unstated band↔tone mapping** (`STATUS.md` lines 103–107 / `HANDOFF.md` lines 150–153). The cross-validation is directionally sound (every preset's r is positive and substantial), but the exact per-preset r values and the "punch is weakest" superlative are not stored and flip under a reasonable alternative mapping (nearest-log-frequency makes **universal** the weakest, not punch). **Fix:** store the mapping + r values in `canonical.json`, or soften the prose to "r roughly 0.6–0.97; natural/oomph strongest, punch/universal weakest."

---

## 3. Analysis

### 3a. Static vs adaptive: BandLab's per-preset EQ is a STATIC, content-independent curve

_Deliverable: `tools/analysis_static_check.py` (run with the repo venv; no files written)._

The EQ curve each preset imposes is **static** — it does not change with the input spectrum or input level. Only makeup gain and dynamics adapt. The evidence is two-fold and mutually reinforcing:

1. **Cross-signal agreement.** The tone ladder and swept sine — two completely different signals — produce essentially identical EQ curves for every preset: **r = 0.985–0.999, RMS 0.06–0.54 dB**. A content-adaptive EQ would respond differently to a single tone vs a sweep; this one does not.
2. **Cross-level stability.** The EQ shape (makeup-normalized) is frozen across the three pink input levels: **cross-level r mean 0.979, shape RMS < 0.76 dB** — even as makeup gain swings **4–7 dB** with level.

Verdict: **7 of 8 presets static**; clarity is flagged only as a borderline measurement-noise case (its -20-vs-10 cross-level r = 0.882 and residual monotonicity 0.79 sit just under conservative 0.90/0.80 thresholds; its shape still moves only 0.76 dB RMS). `overall_static = False` in the JSON solely because of clarity's marginal numbers, not because of any adaptive shaping.

The lower pink-vs-tone correlations (down to r≈0.63) are **not** adaptivity — they are a within-band-slope measurement artifact (pink measures band-integrated energy; the tone ladder samples one frequency per band, so where a preset's EQ has a slope inside a band the two legitimately differ). Proof: the residual is a smooth monotonic ramp vs frequency whose magnitude scales with each preset's tilt steepness (punch steepest → largest residual). This is fully consistent with the already-confirmed peak-normalizer-to-(-4.5)-dBFS input model. (Limitation: dynamics/limiter timing and stereo width were not part of the EQ-shape question and the repo already notes dynamics ARE level-adaptive — this establishes the EQ **curve** is static, which is what was asked.)

### 3b. Preset distinctiveness: only moderately distinct — 6 of 8 collapse into one loose cluster

_Deliverable: `tools/analysis_distinctiveness.py --service bandlab --k 3` (run with the repo venv; no files written)._

BandLab's preset space is dominated by **one loudness axis** (punch loud/crushed at -7.4 LUFS, warm quiet/gentle at -13.8) plus a tonal smear. Once loudness is matched, **6 of 8 presets are near-redundant**; **punch and oomph are the only true outliers**, and **spatial is the lone stereo outlier** (correlation change -0.315 vs the other seven within 0.03 of zero). The 6.4 dB LUFS span is the main thing keeping presets apart, yet warm/clarity/oomph still pile up near -13.

Implications for designing his own distinct presets:

- **(A) Spread output LOUDNESS first** — it gives the cleanest separation. Place targets 2–3 LUFS apart.
- **(B) Treat the 21 tonal columns as ~2 real knobs** (overall tilt + low-shelf-vs-air balance), not 21 — they have the widest ranges but the smeariest, least-separating splits.
- **(C) Exploit STEREO CORRELATION as a free differentiator** — only spatial decorrelates, so a genuinely-wide and a genuinely-narrow preset occupy empty space (trust `correlation_change`, not width-dB).
- **(D) Break the loudness↔dynamics correlation on purpose** to make a "loud-but-open" preset BandLab lacks.
- **(E) Re-run the script on his own presets** and require every pair to exceed BandLab's tape~universal gap (4.31) so no slot is wasted.

Methodology notes that matter: the analysis mean-centers the tonal axes so they measure **color, not loudness** (raw tone gains otherwise just re-encode makeup level); it flags the tonal block as ~2 effective DOF to avoid over-counting tone; it removed a tautology in the first draft (mean pairwise squared z-distance is identically 2.286 for any z-scored 8-column, so it cannot rank axes — replaced with a gap statistic that actually varies); and it keys stereo recommendations off `correlation_change`, not the inflated width-dB. With n=8, single outliers dominate several rankings — directions are robust, exact gap/distance values are indicative.

---

## 4. Bottom Line for the Operator

**Can the fingerprints be trusted? Yes, for their core purpose.** The input→output delta methodology is sound, the -4.5 dBFS peak-normalizer input model is the project's strongest and fully-verified claim, and the per-preset loudness/EQ/dynamics/stereo numbers are correct. There are **no P0 ship-blockers** and almost none of the defects corrupt the currently-committed numbers.

**Two numbers to treat with care before quoting externally:** (1) the **true-peak ceiling** can over-report by ~+1 dB at file boundaries and feeds a hard clip verdict thresholded at exactly 0.0 dBTP — fix the resampler edge trim before trusting any borderline clip/no-clip call (P1); and (2) the **loudness chart bar lengths are inverted** — read the printed numbers/table, not the bar lengths, until that panel is fixed (P1). Beyond those, the **spectral tilt** metric is HF-biased (it understates bass moves ~6x), the **"loudness chase"** and **"widest stereo"** labels overstate/mislabel their effects, and several docstrings/STATUS claims are quantitatively off — all P2/P3, all in the interpretation/report/docs layer rather than the measurement core.

**How distinct are BandLab's presets? Only moderately** — 6 of 8 collapse into one loose cluster once loudness is matched; punch, oomph, and spatial (stereo) are the only genuine outliers, and the whole space is essentially one loudness axis plus a tonal smear.

**What that implies for his own presets:** distinctiveness is cheap to win because BandLab leaves it on the table. Spread output **loudness** first (2–3 LUFS apart), use **stereo correlation** as a free differentiator (almost unused), treat tone as ~2 real knobs not 21, and deliberately build the "loud-but-open" preset BandLab lacks. And because the EQ curve is provably **static**, an emulation recipe can model each preset as a fixed EQ + a level-adaptive makeup/limiter stage — with the one caveat that on heavily-limited presets (punch) the measured EQ shape still blends EQ with frequency-dependent limiting, so separate those two stages when building the recipe.
