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


def _hbar(ax, names, vals, title, xlabel, danger=None, fmt="{:.1f}"):
    order = np.argsort(vals)
    names = [names[i] for i in order]
    vals = [vals[i] for i in order]
    cols = ["#dc2626" if (danger is not None and v > danger) else "#2563eb" for v in vals]
    ax.barh(range(len(names)), vals, color=cols, alpha=0.85)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    if danger is not None:
        ax.axvline(danger, color="#dc2626", ls="--", lw=1)
    for i, v in enumerate(vals):
        ax.text(v, i, " " + fmt.format(v), va="center",
                ha="left" if v >= 0 else "right", fontsize=8)


def chart_loudness_grid(presets) -> str:
    names = list(presets.keys())
    lufs = [presets[n]["loudness"]["output_integrated_lufs"] for n in names]
    makeup = [presets[n]["loudness"]["makeup_gain_db"] for n in names]
    tp = [presets[n]["loudness"]["true_peak_ceiling_dbtp"] for n in names]
    crest = [presets[n]["loudness"]["crest_change_db"] for n in names]
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.2))
    _hbar(axes[0, 0], names, lufs, "Output loudness (louder = up)", "LUFS")
    _hbar(axes[0, 1], names, makeup, "Makeup gain applied", "dB")
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

    charts = []
    if has_eq:
        charts.append(chart_eq_overlay(presets))
        charts.append(chart_loudness_grid(presets))
        charts.append(chart_tilt(presets))

    # derived headline findings
    L = {n: presets[n]["loudness"] for n in presets}
    loudest = max(L, key=lambda n: L[n]["output_integrated_lufs"])
    quietest = min(L, key=lambda n: L[n]["output_integrated_lufs"])
    brightest = max(presets, key=lambda n: presets[n]["spectral_tilt_change_db_per_oct"])
    darkest = min(presets, key=lambda n: presets[n]["spectral_tilt_change_db_per_oct"])
    most_comp = min(L, key=lambda n: L[n]["crest_change_db"])
    clippers = [n for n in L if L[n]["true_peak_ceiling_dbtp"] > 0.0]

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

    imgs = "".join(f"<img src='data:image/png;base64,{c}'/>" for c in charts)
    findings = f"""
      <li><b>Loudest:</b> {loudest} ({L[loudest]['output_integrated_lufs']:.1f} LUFS) ·
          <b>Quietest:</b> {quietest} ({L[quietest]['output_integrated_lufs']:.1f} LUFS)
          — a {L[loudest]['output_integrated_lufs']-L[quietest]['output_integrated_lufs']:.1f} dB spread.</li>
      <li><b>Brightest:</b> {brightest} ({presets[brightest]['spectral_tilt_change_db_per_oct']:+.2f} dB/oct) ·
          <b>Darkest:</b> {darkest} ({presets[darkest]['spectral_tilt_change_db_per_oct']:+.2f} dB/oct).</li>
      <li><b>Most compressed:</b> {most_comp} (crest {L[most_comp]['crest_change_db']:+.2f} dB).</li>
      <li><b>True-peak over 0 dBTP (inter-sample clipping):</b> {', '.join(clippers) if clippers else 'none'}.</li>
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
<h2>Tonal contour</h2>
{f"<img src='data:image/png;base64,{charts[0]}'/>" if has_eq else "<p>No EQ data.</p>"}
<h2>Loudness &amp; limiting</h2>
{f"<img src='data:image/png;base64,{charts[1]}'/>" if has_eq else ""}
{f"<img src='data:image/png;base64,{charts[2]}'/>" if has_eq else ""}
<h2>All measurements</h2>
{table}
<p class='muted'>Full structured data: measurements/fingerprints/{service}/canonical.json</p>
</body></html>"""

    (out_dir / "comparison.html").write_text(html, encoding="utf-8", newline="\n")

    md = [f"# {service} preset comparison",
          f"_{note}_\n",
          "| Preset | Out LUFS | Makeup dB | True-peak dBTP | Crest Δ | Tilt Δ dB/oct |",
          "|---|---|---|---|---|---|"]
    for n, fp in presets.items():
        ld = fp["loudness"]
        md.append(f"| {n} | {ld['output_integrated_lufs']:.2f} | {ld['makeup_gain_db']:.2f} | "
                  f"{ld['true_peak_ceiling_dbtp']:+.2f} | {ld['crest_change_db']:+.2f} | "
                  f"{fp['spectral_tilt_change_db_per_oct']:+.2f} |")
    (out_dir / "comparison.md").write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"Wrote {(out_dir / 'comparison.html').relative_to(ROOT)} "
          f"({(out_dir / 'comparison.html').stat().st_size/1024:.0f} KB)")
    print(f"Wrote {(out_dir / 'comparison.md').relative_to(ROOT)}")
    print(f"Loudest={loudest} Quietest={quietest} Brightest={brightest} Clippers={clippers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
