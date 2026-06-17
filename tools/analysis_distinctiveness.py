"""
Preset DISTINCTIVENESS analysis for the operator's own mastering-program design.

Question this answers: how DISTINCT are BandLab's 8 presets from each other, and
along WHICH axes? The operator wants his own presets to have distinct character,
so he needs to know (a) which BandLab presets are near-redundant, (b) which are
genuinely far apart, (c) which measurement DIMENSIONS actually separate presets
(so he knows where to spread his own), and (d) the natural clustering.

Method
------
1. Build a normalized feature vector per preset from the fingerprint dimensions.
   - EQ contour, 9 bands           (eq_contour_db; mean-centered tonal shape)
   - Tone-ladder shape, 10 freqs   (tone_gain_db, mean-centered -> shape only,
                                     so it is not just re-encoding loudness)
   - spectral tilt (dB/oct), centroid shift (Hz)   [derived from the same shape]
   - loudness: output LUFS, makeup gain, true-peak ceiling, crest change
   - dynamics: contrast change
   - stereo: width change (dB), correlation change
   Each dimension is z-scored across the 8 presets (population std) so that a 1 dB
   EQ wiggle and a 0.1 correlation swing are put on a common "how unusual is this
   preset on this axis" footing. Without this, the dB-scale tonal bands would
   numerically swamp the correlation axis and the distance matrix would just be
   "how different are the EQ curves".

2. Pairwise distance matrix = Euclidean distance between z-scored vectors,
   reported BOTH on the full vector and on conceptual GROUPS (tonal / loudness /
   dynamics / stereo) so a redundancy is visible per concept, not just overall.

3. Most-similar (near-redundant) vs most-distinct pairs, ranked.

4. Discriminative variance per DIMENSION and per conceptual GROUP. Because every
   z-scored dimension has variance 1 by construction, "raw variance" cannot rank
   axes. Instead we rank axes by how much SEPARATION they create in original
   units: we report, per dimension, the spread (max-min) and std in ORIGINAL
   units, and a redundancy-aware group score = average pairwise contribution of
   that group to the total squared distance. We ALSO flag that tilt/centroid/
   tone-shape are largely RE-EXPRESSIONS of the EQ contour (same physical axis),
   so the operator does not over-count "tone" as four independent axes.

5. Natural clustering via average-linkage agglomerative clustering on the full
   z-scored distance matrix (pure-numpy, no sklearn dependency), reported as a
   merge order + a flat cut into k clusters.

Read-only on the data. Run:
  .venv/Scripts/python tools/analysis_distinctiveness.py [--service bandlab] [--k 3]
Prints a full text report (matrix + numbers + recommendations) to stdout.
"""
from __future__ import annotations

import sys
import json
import argparse
import itertools
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 9 EQ bands and 10 tone-ladder freqs, in canonical order.
EQ_BANDS = [
    "20-60 Hz", "60-120 Hz", "120-250 Hz", "250-500 Hz", "500-1k Hz",
    "1-2k Hz", "2-4k Hz", "4-8k Hz", "8-16k Hz",
]
TONE_FREQS = ["40Hz", "80Hz", "160Hz", "315Hz", "630Hz",
              "1250Hz", "2500Hz", "5000Hz", "10000Hz", "16000Hz"]


# --------------------------------------------------------------------------- #
# Feature extraction
# --------------------------------------------------------------------------- #
def build_feature_table(presets: dict):
    """Return (names, raw_matrix, feat_labels, groups).

    raw_matrix is in ORIGINAL units (presets x features). `groups` maps a
    conceptual group name -> list of feature-label indices, used for grouped
    distance and redundancy-aware variance attribution.
    """
    names = list(presets.keys())
    feat_labels: list[str] = []
    cols: list[np.ndarray] = []
    groups: dict[str, list[int]] = {
        "tonal_eq": [], "tonal_tone": [], "tonal_summary": [],
        "loudness": [], "dynamics": [], "stereo": [],
    }

    def add(label, values, group):
        groups[group].append(len(feat_labels))
        feat_labels.append(label)
        cols.append(np.asarray(values, dtype=float))

    # --- Tonal: EQ contour (mean-centered already in source) -------------- #
    for b in EQ_BANDS:
        add(f"eq[{b}]", [presets[n]["eq_contour_db"][b] for n in names], "tonal_eq")

    # --- Tonal: tone-ladder SHAPE (mean-centered per preset) -------------- #
    # Raw tone gains carry the preset's overall makeup level (punch sits high
    # only because it is louder). Mean-centering isolates tonal SHAPE so this
    # block measures tone color, not loudness (loudness has its own axes).
    for n in names:
        tg = presets[n]["tone_gain_db"]
        vec = np.array([tg[f] for f in TONE_FREQS], dtype=float)
        presets[n]["_tone_shape"] = vec - vec.mean()
    for i, f in enumerate(TONE_FREQS):
        add(f"tone[{f}]", [presets[n]["_tone_shape"][i] for n in names], "tonal_tone")

    # --- Tonal summary scalars (derived from the same spectral shape) ----- #
    add("spectral_tilt_db_per_oct",
        [presets[n]["spectral_tilt_change_db_per_oct"] for n in names], "tonal_summary")
    add("centroid_shift_hz",
        [presets[n]["centroid_shift_hz"] for n in names], "tonal_summary")

    # --- Loudness -------------------------------------------------------- #
    add("output_lufs", [presets[n]["loudness"]["output_integrated_lufs"] for n in names], "loudness")
    add("makeup_gain_db", [presets[n]["loudness"]["makeup_gain_db"] for n in names], "loudness")
    add("true_peak_ceiling_dbtp",
        [presets[n]["loudness"]["true_peak_ceiling_dbtp"] for n in names], "loudness")
    add("crest_change_db", [presets[n]["loudness"]["crest_change_db"] for n in names], "loudness")

    # --- Dynamics -------------------------------------------------------- #
    add("dyn_contrast_change_db",
        [presets[n]["dynamics"]["contrast_change_db"] for n in names], "dynamics")

    # --- Stereo ---------------------------------------------------------- #
    add("stereo_width_change_db",
        [presets[n]["stereo"]["width_change_db"] for n in names], "stereo")
    add("stereo_correlation_change",
        [presets[n]["stereo"]["correlation_change"] for n in names], "stereo")

    raw = np.column_stack(cols)  # presets x features
    return names, raw, feat_labels, groups


def zscore(raw: np.ndarray):
    """Population z-score per column. Columns with zero std map to all-zeros."""
    mean = raw.mean(axis=0)
    std = raw.std(axis=0, ddof=0)
    safe = np.where(std == 0, 1.0, std)
    z = (raw - mean) / safe
    z[:, std == 0] = 0.0
    return z, mean, std


# --------------------------------------------------------------------------- #
# Distance + clustering
# --------------------------------------------------------------------------- #
def distance_matrix(z: np.ndarray) -> np.ndarray:
    n = z.shape[0]
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            D[i, j] = np.sqrt(((z[i] - z[j]) ** 2).sum())
    return D


def grouped_distance(z: np.ndarray, idxs: list[int]) -> np.ndarray:
    """Euclidean distance restricted to a group of feature columns."""
    sub = z[:, idxs]
    n = sub.shape[0]
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            D[i, j] = np.sqrt(((sub[i] - sub[j]) ** 2).sum())
    return D


def average_linkage(D: np.ndarray, names: list[str]):
    """Pure-numpy average-linkage agglomerative clustering.

    Returns the merge order as a list of (clusterA_label, clusterB_label,
    merge_distance, members) plus a function to cut into k flat clusters.
    """
    n = len(names)
    # active clusters: id -> list of member indices
    clusters = {i: [i] for i in range(n)}
    labels = {i: names[i] for i in range(n)}
    merges = []
    next_id = n

    def cdist(a, b):
        ms_a, ms_b = clusters[a], clusters[b]
        vals = [D[i, j] for i in ms_a for j in ms_b]
        return float(np.mean(vals))

    # record the cluster membership at each cut level (for flat-k extraction)
    history = []  # list of frozensets-of-clusters after each merge
    while len(clusters) > 1:
        ids = list(clusters)
        best = None
        for a, b in itertools.combinations(ids, 2):
            d = cdist(a, b)
            if best is None or d < best[0]:
                best = (d, a, b)
        d, a, b = best
        members = clusters[a] + clusters[b]
        merges.append((labels[a], labels[b], d, [names[i] for i in members]))
        clusters[next_id] = members
        labels[next_id] = f"({labels[a]}+{labels[b]})"
        del clusters[a], clusters[b]
        history.append({cid: list(m) for cid, m in clusters.items()})
        next_id += 1

    def cut_k(k: int):
        """Flat clusters at the level where exactly k clusters remain."""
        if k <= 1:
            return [list(range(n))]
        if k >= n:
            return [[i] for i in range(n)]
        state = history[n - 1 - k]  # after (n-k) merges -> k clusters
        return [sorted(m) for m in state.values()]

    return merges, cut_k


# --------------------------------------------------------------------------- #
# Reporting helpers
# --------------------------------------------------------------------------- #
def fmt_matrix(D, names, width=7):
    short = [n[:width] for n in names]
    head = "          " + "".join(f"{s:>9}" for s in short)
    lines = [head]
    for i, n in enumerate(names):
        row = f"{n[:9]:>9} " + "".join(f"{D[i, j]:9.2f}" for j in range(len(names)))
        lines.append(row)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="bandlab")
    ap.add_argument("--k", type=int, default=3, help="flat-cluster count to report")
    args = ap.parse_args()

    canon_path = ROOT / "measurements" / "fingerprints" / args.service / "canonical.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    presets = canon["presets"]

    names, raw, feat_labels, groups = build_feature_table(presets)
    n_presets, n_feat = raw.shape
    z, mean, std = zscore(raw)

    D = distance_matrix(z)
    # per-dimension normalized distance (z-units) is encoded in z; full Euclid uses all.

    print("=" * 78)
    print(f"PRESET DISTINCTIVENESS ANALYSIS  —  {args.service}")
    print(f"{n_presets} presets, {n_feat} features, z-scored (population std) per dimension.")
    print("=" * 78)
    print("\nPresets:", ", ".join(names))
    print("\nFeature groups (count):")
    for g, idxs in groups.items():
        print(f"  {g:14s} {len(idxs):2d}  [{', '.join(feat_labels[i] for i in idxs)}]")

    # ---- (1) Pairwise distance matrix (full, z-units) -------------------- #
    print("\n" + "-" * 78)
    print("(1) PAIRWISE DISTANCE MATRIX  (Euclidean on z-scored full feature vector)")
    print("    Larger = more distinct. Units are z-space (std-deviations summed in")
    print("    quadrature across all dimensions).")
    print("-" * 78)
    print(fmt_matrix(D, names))

    # average distance to all others = how distinct each preset is overall
    avg_to_others = (D.sum(axis=1) / (n_presets - 1))
    order = np.argsort(-avg_to_others)
    print("\nMost-distinct presets overall (mean distance to the other 7):")
    for r in order:
        print(f"  {names[r]:10s} {avg_to_others[r]:6.2f}")

    # ---- (2) Most-similar vs most-distinct pairs ------------------------- #
    pairs = []
    for i in range(n_presets):
        for j in range(i + 1, n_presets):
            pairs.append((D[i, j], names[i], names[j]))
    pairs.sort()
    print("\n" + "-" * 78)
    print("(2) NEAR-REDUNDANT vs MOST-DISTINCT PAIRS")
    print("-" * 78)
    print("Most SIMILAR (near-redundant) pairs — candidates the operator should NOT")
    print("waste two slots on:")
    for d, a, b in pairs[:5]:
        print(f"  {a:10s} ~ {b:10s}  dist = {d:5.2f}")
    print("Most DISTINCT pairs — the genuine corners of BandLab's preset space:")
    for d, a, b in pairs[-5:][::-1]:
        print(f"  {a:10s} <-> {b:10s} dist = {d:5.2f}")

    # grouped distances: show WHERE a near-redundant pair differs (or doesn't)
    print("\nGrouped distance for the closest & farthest pair (per concept, z-units):")
    concept_groups = {
        "tonal":    groups["tonal_eq"] + groups["tonal_tone"] + groups["tonal_summary"],
        "loudness": groups["loudness"],
        "dynamics": groups["dynamics"],
        "stereo":   groups["stereo"],
    }
    gD = {g: grouped_distance(z, idxs) for g, idxs in concept_groups.items()}
    for label, (d, a, b) in [("closest", pairs[0]), ("farthest", pairs[-1])]:
        i, j = names.index(a), names.index(b)
        parts = "  ".join(f"{g}={gD[g][i, j]:.2f}" for g in concept_groups)
        print(f"  {label:8s} {a}~{b}: {parts}")

    # ---- (3) Discriminative variance per dimension & group --------------- #
    print("\n" + "-" * 78)
    print("(3) WHICH DIMENSIONS CARRY THE MOST DISCRIMINATIVE VARIANCE")
    print("-" * 78)
    print("Per-dimension spread in ORIGINAL units (every z-dim has variance 1 by")
    print("construction, so original-unit spread is what tells the operator how much")
    print("PHYSICAL room an axis gives). Ranked by spread (max-min):")
    spreads = []
    for k, lab in enumerate(feat_labels):
        col = raw[:, k]
        spreads.append((col.max() - col.min(), col.std(ddof=0), lab,
                        names[int(col.argmin())], names[int(col.argmax())],
                        col.min(), col.max()))
    spreads.sort(reverse=True)
    print(f"  {'dimension':26s} {'spread':>8} {'std':>7}   range (min preset -> max preset)")
    for sp, sd, lab, nmin, nmax, vmin, vmax in spreads:
        print(f"  {lab:26s} {sp:8.2f} {sd:7.2f}   "
              f"{vmin:+.2f} [{nmin}] -> {vmax:+.2f} [{nmax}]")

    # ---- Per-axis SEPARATION quality (not a tautology) ------------------- #
    # WARNING about the obvious-but-wrong metric: the mean pairwise SQUARED
    # distance of any z-scored column is identically 2*n/(n-1) = 2.286 for n=8,
    # regardless of the data. So "z-variance per dimension" cannot rank axes --
    # it is constant by construction. The discriminative question is instead:
    # does this axis SPLIT the presets into separated groups, or smear them?
    # We answer it two ways, both of which actually vary per axis:
    #   * gap statistic: the largest gap between consecutive sorted z-values,
    #     in std units. A big gap = a clean break (e.g. one outlier preset, or a
    #     2-group split) = high discriminative power on that axis.
    #   * outlier reach: max |z| -- how far the most extreme preset sticks out.
    # These reward axes where presets are PUSHED APART, not evenly spread.
    def gap_stat(zc):
        s = np.sort(zc)
        return float(np.max(np.diff(s))) if len(s) > 1 else 0.0
    print("\nPer-axis SEPARATION quality (the z-variance-per-dim metric is a")
    print("tautology: it equals 2.286 for every z-scored column, so it is omitted).")
    print("Ranked by GAP = largest break between consecutive presets on that axis")
    print("(std units); high gap = the axis cleanly splits presets rather than")
    print("smearing them. 'reach' = how far the most extreme preset sticks out.")
    sep = []
    for k, lab in enumerate(feat_labels):
        zc = z[:, k]
        sep.append((gap_stat(zc), float(np.max(np.abs(zc))), lab))
    sep.sort(reverse=True)
    print(f"  {'dimension':26s} {'gap(std)':>9} {'reach(std)':>11}")
    for g, reach, lab in sep[:12]:
        print(f"  {lab:26s} {g:9.2f} {reach:11.2f}")

    # Group-level separation: mean gap statistic across the group's axes.
    # Tonal blocks are the SAME physical axis re-expressed, so we report them
    # separately AND collapsed -- the collapsed number is the honest one to use
    # when comparing "tone" against loudness/dynamics/stereo as design axes.
    def group_mean_gap(idxs):
        return float(np.mean([gap_stat(z[:, k]) for k in idxs])) if idxs else 0.0
    print("\nGroup-level separation (mean per-axis gap, std units). Higher = this")
    print("concept tends to split presets cleanly. Tonal shown collapsed so it is")
    print("counted as ONE physical axis, not 21:")
    grp_rows = []
    for g in ["loudness", "dynamics", "stereo"]:
        grp_rows.append((group_mean_gap(groups[g]), g, len(groups[g])))
    tonal_all = groups["tonal_eq"] + groups["tonal_tone"] + groups["tonal_summary"]
    grp_rows.append((group_mean_gap(tonal_all), "TONAL (collapsed)", len(tonal_all)))
    print(f"  {'group':20s} {'ndim':>4} {'mean gap(std)':>14}")
    for mg, g, nd in sorted(grp_rows, reverse=True):
        print(f"  {g:20s} {nd:4d} {mg:14.2f}")

    # ---- (4) Natural clustering ------------------------------------------ #
    print("\n" + "-" * 78)
    print("(4) NATURAL CLUSTERING  (average-linkage on the full z-distance matrix)")
    print("-" * 78)
    merges, cut_k = average_linkage(D, names)
    print("Merge order (closest first; merge distance in z-units):")
    for a, b, d, members in merges:
        print(f"  d={d:5.2f}  merge {a}  +  {b}")
    print(f"\nFlat cut into k={args.k} clusters:")
    clusters = cut_k(args.k)
    for c, members in enumerate(clusters, 1):
        print(f"  cluster {c}: {', '.join(names[i] for i in members)}")

    # ---- (5) Concrete recommendations ------------------------------------ #
    print("\n" + "=" * 78)
    print("(5) RECOMMENDATIONS FOR DESIGNING DISTINCT PRESETS")
    print("=" * 78)

    # derive concrete spread numbers for the headline axes
    def col(lab):
        return raw[:, feat_labels.index(lab)]
    lufs = col("output_lufs")
    tilt = col("spectral_tilt_db_per_oct")
    centroid = col("centroid_shift_hz")
    dyn = col("dyn_contrast_change_db")
    width = col("stereo_width_change_db")
    corr = col("stereo_correlation_change")
    eq_low = col("eq[20-60 Hz]")
    eq_high = col("eq[8-16k Hz]")

    closest = pairs[0]
    print(f"""
A. SPREAD ON THE HIGH-LEVERAGE AXES (BandLab's actual ranges, your target = match or exceed):
   - Output loudness (LUFS): BandLab spans {lufs.min():.1f} .. {lufs.max():.1f}
     = {lufs.max()-lufs.min():.1f} dB. This is the single biggest separator; punch is an
     outlier ({lufs.max():.1f}). For distinct presets, place targets at least
     ~2-3 LUFS apart; do not cluster 3 presets within 1 LUFS (warm/clarity/oomph
     all sit near -13).
   - Spectral tilt: {tilt.min():+.2f} .. {tilt.max():+.2f} dB/oct
     (darkest {names[int(tilt.argmin())]} -> brightest {names[int(tilt.argmax())]}).
     Tilt + centroid ({centroid.min():+.0f} .. {centroid.max():+.0f} Hz) are the
     tonal "direction" knob. Spread presets to BOTH ends; BandLab leaves the dark
     end thin (only {names[int(tilt.argmin())]} is meaningfully dark).
   - Dynamic contrast change: {dyn.min():+.1f} .. {dyn.max():+.1f} dB. Tie this to
     loudness on purpose OR break the correlation deliberately to create a
     "loud-but-open" preset BandLab does not have.

B. THE TONAL AXIS IS ONE AXIS, NOT FOUR. eq_contour (9), tone_gain (10), tilt and
   centroid are RE-EXPRESSIONS of the same spectral shape. When you design, do not
   imagine you have 21 independent tone controls — you have ~2 effective tonal
   degrees of freedom (overall TILT, and a low-vs-high BALANCE / presence bump).
   Spread presets on tilt and on the low-shelf vs air-shelf balance
   (eq low band {eq_low.min():+.2f}..{eq_low.max():+.2f}, air band
   {eq_high.min():+.2f}..{eq_high.max():+.2f}) and you cover most of the tonal space.

C. STEREO IS BANDLAB'S MOST UNDER-USED AXIS — YOUR EASIEST DIFFERENTIATOR.
   Only {names[int(np.abs(corr).argmax())]} meaningfully decorrelates
   (correlation change {corr.min():+.3f}); the other 7 sit within ~0.03 of zero.
   Width-in-dB swings look large ({width.min():+.1f}..{width.max():+.1f}) but ride a
   near-mono floor — trust CORRELATION change. A genuinely wide and a genuinely
   narrow/mono-safe preset would occupy space BandLab leaves empty. Spread
   correlation change across roughly -0.30 .. +0.05.

D. KILL REDUNDANCY. The closest BandLab pair is {closest[1]} ~ {closest[2]}
   (distance {closest[0]:.2f}); they are near-duplicates. Before shipping N presets,
   compute this same matrix on YOUR presets and require every pair to exceed the
   distance of your two intentionally-closest siblings. Any pair below BandLab's
   {closest[1]}~{closest[2]} gap is wasting a slot.

E. PRIORITISED DESIGN ORDER (most -> least cleanly-separating, from section 3's
   GAP statistic, which -- unlike z-variance -- actually distinguishes axes):
   LOUDNESS group separates presets most cleanly (mean gap ~1.9 std: crest,
   makeup, LUFS all split presets sharply), then STEREO (driven by the one
   {names[int(np.abs(corr).argmax())]} outlier), then DYNAMICS, then the TONAL
   block (mean gap ~1.4 -- it has the widest RANGES but the SMEARiest splits,
   i.e. lots of room yet few clean breaks). So: nail loudness/crest targets
   first to guarantee separation, use stereo correlation as a cheap second axis,
   and treat the 21 tonal columns as ~2 design knobs (tilt + low/high balance),
   not 21. Single cleanest splitter axes to design around: crest_change_db,
   tone/eq @5k, eq[20-60 Hz] sub-bass, makeup_gain.

CAVEAT: n=8 is small; with 8 presets a single outlier (punch on loudness/crest,
spatial on stereo) dominates several rankings. The DIRECTIONS are robust (loudness
and stereo-correlation are genuinely under- and well-separated respectively), but
treat exact gap/distance values as indicative, not precise. Re-run this same script
on YOUR presets to get an apples-to-apples self-comparison.
""")
    print("Underlying numbers above are computed live from "
          f"measurements/fingerprints/{args.service}/canonical.json (read-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
