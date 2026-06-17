"""
Render the human-readable preset COMPARISON report from a service canonical.json.

Overlays every preset's tonal contour and ranks loudness / limiting behavior.
Scales automatically: sections appear only for dimensions the present signals
support (pink_noise -> EQ + loudness today; tone/dynamic/stereo/click when added).

Run:  .venv/Scripts/python tools/compare.py --service bandlab
Writes: reports/fingerprints/<service>/comparison.html  (+ comparison.md)
"""
from __future__ import annotations

import sys
import json
import base64
import argparse
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import signals as sigreg

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "#fafafa",
    "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.7,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "figure.dpi": 110,
})

BANDS = sigreg.SPECTRAL_BANDS
BAND_LABELS = [b[0] for b in BANDS]
BAND_CENTERS = [float(np.sqrt(b[1] * b[2])) for b in BANDS]  # geometric centers


def _b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _colors(n):
    cmap = plt.get_cmap("tab10")
    return [cmap(i % 10) for i in range(n)]


def chart_eq_overlay(presets) -> str:
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    cols = _colors(len(presets))
    for (name, fp), c in zip(presets.items(), cols):
        contour = fp.get("eq_contour_db")
        if not contour:
            continue
        y = [contour[b] for b in BAND_LABELS]
        ax.semilogx(BAND_CENTERS, y, "o-", color=c, lw=1.8, ms=4, label=name)
    ax.axhline(0, color="#111", lw=1, alpha=0.5)
    ax.set_xlabel("Frequency (Hz, band geometric center)")
    ax.set_ylabel("Tonal contour (dB, mean-centered)")
    ax.set_title("Preset EQ contour on neutral pink noise  —  what each preset does tonally")
    ax.set_xticks(BAND_CENTERS)
    ax.set_xticklabels([f"{int(round(c))}" for c in BAND_CENTERS], fontsize=8)
    ax.legend(fontsize=8, ncol=2, loc="upper center")
    return _b64(fig)


def _hbar(ax, names, vals, title, xlabel, danger=None, fmt="{:.1f}", labels=None):
    # `labels` lets the bar TEXT show a different value than the plotted length
    # (used when a panel plots a transformed quantity, e.g. LU-below-loudest, but
    # should annotate the true absolute value).
    order = np.argsort(vals)
    names = [names[i] for i in order]
    vals = [vals[i] for i in order]
    txt = [labels[i] for i in order] if labels is not None else vals
    cols = ["#dc2626" if (danger is not None and v > danger) else "#2563eb" for v in vals]
    ax.barh(range(len(names)), vals, color=cols, alpha=0.85)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.margins(x=0.18)  # headroom so value labels don't collide with axis/ticks
    if danger is not None:
        ax.axvline(danger, color="#dc2626", ls="--", lw=1)
    for i, v in enumerate(vals):
        ax.text(v, i, " " + fmt.format(txt[i]) + " ", va="center",
                ha="left" if v >= 0 else "right", fontsize=8)


def chart_loudness_grid(presets) -> str:
    names = list(presets.keys())
    lufs = [presets[n]["loudness"]["output_integrated_lufs"] for n in names]
    makeup = [presets[n]["loudness"]["makeup_gain_db"] for n in names]
    tp = [presets[n]["loudness"]["true_peak_ceiling_dbtp"] for n in names]
    crest = [presets[n]["loudness"]["crest_change_db"] for n in names]
    # Plot loudness as LU-below-loudest (0 = loudest), NOT absolute LUFS: absolute
    # values are all negative, so a bar drawn from 0 would make the loudest preset
    # the SHORTEST bar (inverted). Length now = how much quieter than the loudest;
    # labels still show the true LUFS.
    lmax = max(lufs)
    lufs_below = [v - lmax for v in lufs]
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.2))
    _hbar(axes[0, 0], names, lufs_below, "Output loudness — LU below loudest (0 = loudest)",
          "LU below loudest", labels=lufs)
    _hbar(axes[0, 1], names, makeup, "Makeup gain applied (RMS delta)", "dB")
    _hbar(axes[1, 0], names, tp, "True-peak ceiling (>0 = clips)", "dBTP", danger=0.0)
    _hbar(axes[1, 1], names, crest, "Crest-factor change (more neg = more compressed)", "dB")
    fig.tight_layout()
    return _b64(fig)


def chart_tilt(presets) -> str:
    names = list(presets.keys())
    tilt = [presets[n]["spectral_tilt_change_db_per_oct"] for n in names]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    _hbar(ax, names, tilt, "Spectral tilt change (+ = brighter, - = darker)", "dB/oct", fmt="{:+.2f}")
    return _b64(fig)


# --------------------------------------------------------------------------- #
# Sections that light up as the later signals land (gated on data presence).
# --------------------------------------------------------------------------- #
_PINK_LEVELS = [("pink_noise_minus20.wav", -20), ("pink_noise_minus14.wav", -14),
                ("pink_noise_minus10.wav", -10)]


def chart_level_dependence(presets):
    """Loudness lift (LUFS) vs input level — the adaptive loudness-chase fingerprint.
    Plotted in LUFS, not RMS: a spectrum-reshaping preset (e.g. warm cuts sub, lifts
    highs) can DROP RMS while LUFS RISES, so RMS misrepresents the chase (verified)."""
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    cols = _colors(len(presets))
    any_data = False
    for (name, fp), c in zip(presets.items(), cols):
        ld = (fp.get("level_dependence") or {}).get("loudness_lift_lufs_by_input_level", {})
        pts = [(lvl, ld[fn]) for fn, lvl in _PINK_LEVELS if ld.get(fn) is not None]
        if len(pts) < 2:
            continue
        any_data = True
        xs, ys = zip(*pts)
        ax.plot(xs, ys, "o-", color=c, lw=1.8, ms=5, label=name)
    if not any_data:
        plt.close(fig)
        return None
    ax.set_xlabel("Input level (dBFS RMS, nominal) — quiet to loud  (note: -14/-10 inputs peak near 0 dBFS,\n"
                  "so part of the lift drop at hot input is headroom-limited, not purely adaptive)")
    ax.set_ylabel("Loudness lift (LU, output - input)")
    ax.set_title("Level dependence — loudness lift vs input level  (falling = adaptive loudness chase)")
    ax.set_xticks([-20, -14, -10])  # quiet -> loud, left -> right; lift falls = chasing a target
    ax.legend(fontsize=8, ncol=2)
    return _b64(fig)


def chart_tone_gain(presets):
    """Per-frequency gain from the discrete tone ladder — exact dB per frequency."""
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    cols = _colors(len(presets))
    any_data = False
    for (name, fp), c in zip(presets.items(), cols):
        tg = fp.get("tone_gain_db")
        if not tg:
            continue
        items = sorted((int(k[:-2]), v) for k, v in tg.items() if v is not None)
        if not items:
            continue
        any_data = True
        xs, ys = zip(*items)
        ys = np.array(ys) - float(np.mean(ys))   # mean-center to match eq_contour_db (drops the makeup offset)
        ax.semilogx(xs, ys, "o-", color=c, lw=1.6, ms=4, label=name)
    if not any_data:
        plt.close(fig)
        return None
    ax.axhline(0, color="#111", lw=1, alpha=0.4)
    ax.set_xlabel("Tone frequency (Hz)")
    ax.set_ylabel("Per-frequency gain (dB, mean-centered)")
    ax.set_title("Per-frequency gain (tone ladder, mean-centered) — same convention as the EQ contour, so the shapes overlay")
    ax.legend(fontsize=8, ncol=2)
    return _b64(fig)


def chart_dynamics(presets):
    """How much each preset compresses the 20 dB loud/quiet contrast."""
    names = [n for n in presets
             if (presets[n].get("dynamics") or {}).get("contrast_change_db") is not None]
    if not names:
        return None
    vals = [presets[n]["dynamics"]["contrast_change_db"] for n in names]
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    _hbar(ax, names, vals, "Dynamic contrast change (more negative = more crushed)",
          "dB", fmt="{:+.1f}")
    return _b64(fig)


def chart_stereo(presets):
    """Stereo-width behavior from the mid/side test signal."""
    names = [n for n in presets
             if (presets[n].get("stereo") or {}).get("width_change_db") is not None]
    if not names:
        return None
    width = [presets[n]["stereo"]["width_change_db"] for n in names]
    corr = [presets[n]["stereo"].get("correlation_change") or 0.0 for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    # correlation_change is the trustworthy metric -> left (read first). width-dB rides a
    # near-mono floor (side ~24 dB below mid) and overstates swings -> right, secondary.
    _hbar(axes[0], names, corr, "L/R correlation change (- = wider/decorrelated) — trusted", "", fmt="{:+.3f}")
    _hbar(axes[1], names, width, "Stereo width change in dB — inflated by near-mono floor", "dB (side - mid)", fmt="{:+.1f}")
    fig.tight_layout()
    return _b64(fig)


def chart_click(presets):
    """Honest click-track metrics. The old transient_peak/release 'limiter timing' was
    refuted (it tracked per-preset click WIDENING through a 1 ms envelope, not limiting).
    What the sparse click CAN show: whether clicks survive to clip (output true-peak),
    and how hard the preset pulls up sparse transients (loudness lift)."""
    names = [n for n in presets
             if (presets[n].get("click_response") or {}).get("output_true_peak_dbtp") is not None]
    if not names:
        return None
    tp = [presets[n]["click_response"]["output_true_peak_dbtp"] for n in names]
    lift = [presets[n]["click_response"]["loudness_lift_lufs"] for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    _hbar(axes[0], names, tp, "Click true-peak (>0 = clips)", "dBTP", danger=0.0, fmt="{:+.2f}")
    _hbar(axes[1], names, lift, "Click loudness lift (transient pull-up)", "LU", fmt="{:+.1f}")
    fig.suptitle("Click-track transient handling", fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _b64(fig)


BADGE_CSS = "padding:2px 8px;border-radius:5px;font-weight:700;font-size:12px;color:#fff"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="bandlab")
    args = ap.parse_args()
    service = args.service

    canon_path = ROOT / "measurements" / "fingerprints" / service / "canonical.json"
    if not canon_path.exists():
        print(f"No canonical.json for {service}. Run fingerprint.py first.")
        return 1
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    presets = canon["presets"]
    if not presets:
        print("No presets in canonical.")
        return 1

    out_dir = ROOT / "reports" / "fingerprints" / service
    out_dir.mkdir(parents=True, exist_ok=True)

    # signals actually present across presets
    present = sorted({s for fp in presets.values() for s in fp.get("signals_present", [])})
    has_eq = any("eq_contour_db" in fp for fp in presets.values())

    # Each chart returns a base64 PNG, or None when its source signal is absent.
    chart = {
        "eq": chart_eq_overlay(presets) if has_eq else None,
        "loudness": chart_loudness_grid(presets) if has_eq else None,
        "tilt": chart_tilt(presets) if has_eq else None,
        "tone": chart_tone_gain(presets),
        "level": chart_level_dependence(presets),
        "dynamics": chart_dynamics(presets),
        "stereo": chart_stereo(presets),
        "click": chart_click(presets),
    }

    def section(title, key, blurb=""):
        """Render an <h2> + chart only when that chart has data."""
        if not chart.get(key):
            return ""
        intro = f"<p class='muted'>{blurb}</p>" if blurb else ""
        return (f"<h2>{title}</h2>{intro}"
                f"<img src='data:image/png;base64,{chart[key]}'/>")

    # derived headline findings
    L = {n: presets[n]["loudness"] for n in presets}
    loudest = max(L, key=lambda n: L[n]["output_integrated_lufs"])
    quietest = min(L, key=lambda n: L[n]["output_integrated_lufs"])
    brightest = max(presets, key=lambda n: presets[n]["spectral_tilt_change_db_per_oct"])
    darkest = min(presets, key=lambda n: presets[n]["spectral_tilt_change_db_per_oct"])
    most_comp = min(L, key=lambda n: L[n]["crest_change_db"])
    clippers = [n for n in L if L[n]["true_peak_ceiling_dbtp"] > 0.0]

    # derived findings from the later signals (None-safe; only used if present).
    # Level slope is measured in LUFS (the honest loudness chase), not RMS.
    def _level_slope(n):
        ld = (presets[n].get("level_dependence") or {}).get("loudness_lift_lufs_by_input_level", {})
        g20, g10 = ld.get("pink_noise_minus20.wav"), ld.get("pink_noise_minus10.wav")
        return (g10 - g20) if (g20 is not None and g10 is not None) else None
    level_slopes = {n: s for n in presets if (s := _level_slope(n)) is not None}
    dyn = {n: presets[n]["dynamics"]["contrast_change_db"] for n in presets
           if (presets[n].get("dynamics") or {}).get("contrast_change_db") is not None}
    wid = {n: presets[n]["stereo"]["width_change_db"] for n in presets
           if (presets[n].get("stereo") or {}).get("width_change_db") is not None}
    corr_ch = {n: presets[n]["stereo"]["correlation_change"] for n in presets
               if (presets[n].get("stereo") or {}).get("correlation_change") is not None}
    hardest_chase = min(level_slopes, key=level_slopes.get) if level_slopes else None
    most_crushed = min(dyn, key=dyn.get) if dyn else None
    # widest = most-negative correlation change (the trusted metric); NOT width-dB,
    # which rides a near-mono floor and overstates swings.
    widest = min(corr_ch, key=corr_ch.get) if corr_ch else None

    # table
    cols = ["Preset", "Out LUFS", "Makeup dB", "True-peak dBTP", "Crest Δ dB", "Tilt Δ dB/oct", "Centroid Δ Hz"]
    rows = []
    for n, fp in presets.items():
        ld = fp["loudness"]
        tp = ld["true_peak_ceiling_dbtp"]
        tp_cell = f"<b style='color:#dc2626'>{tp:+.2f}</b>" if tp > 0 else f"{tp:+.2f}"
        rows.append(
            f"<tr><td><b>{n}</b></td><td class='num'>{ld['output_integrated_lufs']:.2f}</td>"
            f"<td class='num'>{ld['makeup_gain_db']:.2f}</td><td class='num'>{tp_cell}</td>"
            f"<td class='num'>{ld['crest_change_db']:+.2f}</td>"
            f"<td class='num'>{fp['spectral_tilt_change_db_per_oct']:+.2f}</td>"
            f"<td class='num'>{fp['centroid_shift_hz']:+.0f}</td></tr>")
    thead = "".join(f"<th>{c}</th>" for c in cols)
    table = f"<table class='cmp'><tr>{thead}</tr>{''.join(rows)}</table>"

    extra = ""
    if hardest_chase:
        extra += (f"<li><b>Hardest loudness chase (level-dependent):</b> {hardest_chase} "
                  f"(loudness lift falls {level_slopes[hardest_chase]:+.1f} LU as input goes -20 to -10 dBFS) — "
                  f"the most adaptive gain.</li>")
    if most_crushed:
        extra += (f"<li><b>Most dynamics-crushing:</b> {most_crushed} "
                  f"(20 dB loud/quiet contrast cut by {dyn[most_crushed]:+.1f} dB).</li>")
    if widest:
        extra += (f"<li><b>Widest stereo:</b> {widest} "
                  f"(correlation change {corr_ch[widest]:+.3f} — the trusted metric; "
                  f"width {wid.get(widest, float('nan')):+.1f} dB rides a near-mono floor).</li>")
    findings = f"""
      <li><b>Loudest:</b> {loudest} ({L[loudest]['output_integrated_lufs']:.1f} LUFS) ·
          <b>Quietest:</b> {quietest} ({L[quietest]['output_integrated_lufs']:.1f} LUFS)
          — a {L[loudest]['output_integrated_lufs']-L[quietest]['output_integrated_lufs']:.1f} dB spread.</li>
      <li><b>Brightest:</b> {brightest} ({presets[brightest]['spectral_tilt_change_db_per_oct']:+.2f} dB/oct) ·
          <b>Darkest:</b> {darkest} ({presets[darkest]['spectral_tilt_change_db_per_oct']:+.2f} dB/oct).</li>
      <li><b>Most compressed:</b> {most_comp} (crest {L[most_comp]['crest_change_db']:+.2f} dB).</li>
      <li><b>True-peak over 0 dBTP (inter-sample clipping):</b> {', '.join(clippers) if clippers else 'none'}.</li>
      {extra}
    """

    note = ("Based on <b>1 signal</b> (pink_noise_minus20) so far — this is the tonal + loudness "
            "fingerprint. Dynamics, stereo width, per-frequency gain, and limiter timing fill in "
            "as the other 7 signals are added.") if present == ["pink_noise_minus20.wav"] else \
           f"Based on signals: {', '.join(present)}."

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{service} preset comparison</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:24px auto;
   color:#1f2937;padding:0 18px;line-height:1.45}}
 h1{{margin-bottom:2px}}
 .hero{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;margin:14px 0}}
 table.cmp{{border-collapse:collapse;width:100%;margin:10px 0}}
 table.cmp td,table.cmp th{{border:1px solid #e5e7eb;padding:6px 9px;text-align:left}}
 table.cmp th{{background:#f3f4f6}}
 .num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace;text-align:right}}
 img{{max-width:100%;border:1px solid #e5e7eb;border-radius:6px;margin:10px 0;background:#fff}}
 ul.find li{{margin:3px 0}}
 .muted{{color:#6b7280;font-size:13px}}
</style></head><body>
<h1>{service} — preset comparison</h1>
<p class='muted'>Generated {canon['generated_utc']} · {len(presets)} presets · {note}</p>
<div class='hero'><b>How to read this.</b> All presets were fed the same neutral pink noise at
 <b>input gain 0</b>, intensity <b>Normal</b>. The EQ contour is mean-centered (0 = no tonal change);
 loudness and limiting are measured as deltas from the input. Same input, so every difference below is
 the preset.
 <ul class='find'>{findings}</ul>
</div>
{section("Tonal contour", "eq",
         "Mean-centered EQ curve on neutral pink noise — the preset's tonal signature.")
 or ("<h2>Tonal contour</h2><p>No EQ data.</p>")}
{section("Loudness &amp; limiting", "loudness")}
{f"<img src='data:image/png;base64,{chart['tilt']}'/>" if chart['tilt'] else ""}
{section("Per-frequency gain (tone ladder)", "tone",
         "Exact dB applied at each discrete tone — independent cross-check of the pink-noise contour.")}
{section("Level dependence (adaptive loudness chase)", "level",
         "Same preset, three input levels, plotted as LUFS lift (not RMS — RMS misreports presets that "
         "reshape spectrum). A downward slope means the chain pulls back loudness lift on hotter input — "
         "it chases a loudness target rather than applying a fixed gain.")}
{section("Dynamics", "dynamics",
         "Change in the 20 dB loud/quiet contrast of the dynamic test. All values negative = every "
         "preset compresses; more negative = more crushed. Compression intensity is strongly but "
         "imperfectly correlated with loudness (r about -0.79) — endpoints match, the middle does not.")}
{section("Stereo width", "stereo",
         "From the mid/side test (the only non-mono signal in the battery). Negative correlation change "
         "is the trustworthy metric; width in dB sits on a near-mono floor (input side ~24 dB below mid) "
         "so it can swing more dramatically than the perceptual change.")}
{section("Click-track transient handling", "click",
         "From the sparse 1-sample click train. NOTE: limiter release/attack CANNOT be read from this "
         "signal (the old transient-peak metric was refuted — it tracked click widening, not limiting). "
         "What is honest: output true-peak (do clicks survive to clip?) and loudness lift (how hard the "
         "preset pulls up sparse transients — punch stands alone).")}
<h2>All measurements</h2>
{table}
<p class='muted'>Full structured data: measurements/fingerprints/{service}/canonical.json</p>
</body></html>"""

    (out_dir / "comparison.html").write_text(html, encoding="utf-8", newline="\n")

    def _cell(v, fmt="{:+.2f}"):
        return fmt.format(v) if v is not None else "—"
    md = [f"# {service} preset comparison",
          f"_{note}_\n",
          "| Preset | Out LUFS | Makeup dB (RMS) | True-peak dBTP | Crest Δ | Tilt Δ dB/oct | "
          "Dynamics Δ dB | Width Δ dB | Level slope LU |",
          "|---|---|---|---|---|---|---|---|---|"]
    for n, fp in presets.items():
        ld = fp["loudness"]
        md.append(f"| {n} | {ld['output_integrated_lufs']:.2f} | {ld['makeup_gain_db']:.2f} | "
                  f"{ld['true_peak_ceiling_dbtp']:+.2f} | {ld['crest_change_db']:+.2f} | "
                  f"{fp['spectral_tilt_change_db_per_oct']:+.2f} | "
                  f"{_cell(dyn.get(n))} | {_cell(wid.get(n))} | {_cell(level_slopes.get(n))} |")
    (out_dir / "comparison.md").write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"Wrote {(out_dir / 'comparison.html').relative_to(ROOT)} "
          f"({(out_dir / 'comparison.html').stat().st_size/1024:.0f} KB)")
    print(f"Wrote {(out_dir / 'comparison.md').relative_to(ROOT)}")
    print(f"Loudest={loudest} Quietest={quietest} Brightest={brightest} Clippers={clippers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
