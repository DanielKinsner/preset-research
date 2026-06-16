"""
Render the human-readable validation report (Step 4, human format).

Reads measurements/validation/*.json and the source WAVs, builds overlay charts
with matplotlib, and emits a single self-contained HTML lab report (charts
embedded as base64 PNG) plus a markdown summary.

Run:  .venv/Scripts/python tools/report.py
"""
from __future__ import annotations

import sys
import json
import base64
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
from scipy import signal as sps

import audio_metrics as am
import signals as sigreg

SRC = ROOT / "source" / "test-signals"
VAL = ROOT / "measurements" / "validation"
REP = ROOT / "reports" / "validation"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "#fafafa",
    "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.7,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "figure.dpi": 110,
})
ACCENT = "#2563eb"


def _b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def chart_pink_overlay() -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = {"pink_noise_minus20.wav": ACCENT,
              "pink_noise_minus14.wav": "#16a34a",
              "pink_noise_minus10.wav": "#dc2626"}
    ref_drawn = False
    for fn, c in colors.items():
        a = am.load_audio(SRC / fn)
        mono = a["data"].mean(axis=1)
        f, pxx = sps.welch(mono, a["sample_rate"], nperseg=16384)
        m = (f >= 20) & (f <= 20000)
        ydb = 10 * np.log10(pxx[m] + 1e-30)
        ax.semilogx(f[m], ydb, color=c, lw=1.3, label=fn.replace(".wav", ""))
        if not ref_drawn:
            # -3 dB/oct reference anchored to the -20 curve at 1 kHz
            k = np.argmin(np.abs(f[m] - 1000))
            ref = ydb[k] - 3.01 * np.log2(f[m] / 1000.0)
            ax.semilogx(f[m], ref, "k--", lw=1.0, alpha=0.6, label="-3.01 dB/oct ref")
            ref_drawn = True
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("PSD (dB)")
    ax.set_title("Pink noise PSD across levels vs ideal -3 dB/oct slope")
    ax.legend(fontsize=8, loc="lower left")
    ax.set_xlim(20, 20000)
    return _b64(fig)


def chart_bands(rec) -> str:
    bands = rec["measurement"]["spectral"]["bands_dbfs"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    names = list(bands.keys()); vals = list(bands.values())
    ax.bar(range(len(names)), vals, color=ACCENT, alpha=0.85)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("Energy (dBFS-equiv)")
    ax.set_title("Per-band energy — pink_noise_minus20 (baseline EQ reference)")
    return _b64(fig)


def chart_tone(rec) -> str:
    tones = rec["measurement"]["signal_specific"]["tones"]
    exp = [t["expected_hz"] for t in tones]
    meas = [t["measured_hz"] for t in tones]
    lvl = [t["level_dbfs"] for t in tones]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.4))
    ax1.loglog(exp, meas, "o", color=ACCENT)
    lim = [min(exp) * 0.8, max(exp) * 1.2]
    ax1.loglog(lim, lim, "k--", alpha=0.5, lw=1)
    ax1.set_xlabel("Expected (Hz)"); ax1.set_ylabel("Measured (Hz)")
    ax1.set_title("Tone freq: measured vs expected")
    ax2.plot(range(len(lvl)), lvl, "o-", color="#16a34a")
    ax2.set_xlabel("Tone segment"); ax2.set_ylabel("Level (dBFS)")
    ax2.set_title("Per-tone level (flat = equal amplitude)")
    ax2.set_ylim(min(lvl) - 1.5, max(lvl) + 1.5)
    return _b64(fig)


def chart_click() -> str:
    a = am.load_audio(SRC / "click_track.wav")
    mono = a["data"].mean(axis=1); sr = a["sample_rate"]
    n = int(5 * sr)
    t = np.arange(n) / sr
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.plot(t, mono[:n], color=ACCENT, lw=0.8)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Amplitude")
    ax.set_title("Click track — first 5 s (impulses every 500 ms)")
    return _b64(fig)


def chart_dynamic(rec) -> str:
    segs = rec["measurement"]["signal_specific"]["segments"]
    vals = [s["rms_dbfs"] for s in segs]
    med = float(np.median(vals))
    colors = ["#dc2626" if v >= med else "#64748b" for v in vals]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar([s["t_start_sec"] for s in segs], vals, width=4, color=colors, alpha=0.85)
    ss = rec["measurement"]["signal_specific"]
    ax.set_xlabel("Segment start (s)"); ax.set_ylabel("RMS (dBFS)")
    ax.set_title(f"Dynamic test — loud vs quiet (contrast {ss['contrast_db']:.1f} dB)")
    return _b64(fig)


def chart_sweep() -> str:
    a = am.load_audio(SRC / "sine_sweep_minus20.wav")
    mono = a["data"].mean(axis=1); sr = a["sample_rate"]
    f, t, Sxx = sps.spectrogram(mono, sr, nperseg=4096, noverlap=2048)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-12), shading="gouraud", cmap="magma")
    ax.set_yscale("log"); ax.set_ylim(20, 20000)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Frequency (Hz)")
    ax.set_title("Sine sweep spectrogram (20 Hz -> 20 kHz log)")
    return _b64(fig)


def chart_midside(rec) -> str:
    st = rec["measurement"]["stereo"]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(["mid", "side"], [st["mid_rms_dbfs"], st["side_rms_dbfs"]],
           color=[ACCENT, "#f59e0b"], alpha=0.85)
    ax.set_ylabel("RMS (dBFS)")
    ax.set_title(f"Mid/Side balance — corr={st['correlation']:.3f}")
    return _b64(fig)


# --------------------------------------------------------------------------- #
# HTML assembly
# --------------------------------------------------------------------------- #
BADGE = {"PASS": ("#16a34a", "PASS"), "WARN": ("#d97706", "WARN"), "FAIL": ("#dc2626", "FAIL")}


def badge(status):
    c, t = BADGE[status]
    return f'<span style="background:{c};color:#fff;padding:2px 9px;border-radius:5px;font-weight:700;font-size:12px">{t}</span>'


def metrics_table(rec):
    m = rec["measurement"]
    rows = [
        ("Sample rate / depth", f"{m['format']['sample_rate']} Hz / {m['format']['bit_depth']}"),
        ("Channels / duration", f"{m['format']['channels']} ch / {m['format']['duration_sec']} s"),
        ("Peak / True-peak", f"{m['levels']['peak_dbfs']:.2f} dBFS / {m['levels']['true_peak_dbtp']:.2f} dBTP"),
        ("RMS / Crest factor", f"{m['levels']['rms_dbfs']:.2f} dBFS / {m['levels']['crest_factor_db']:.2f} dB"),
        ("Integrated loudness / LRA", f"{m['loudness']['integrated_lufs']:.2f} LUFS / {m['loudness']['lra_lu']:.2f} LU"),
        ("Spectral centroid / slope", f"{m['spectral']['centroid_hz']:.0f} Hz / {m['spectral']['slope_db_per_oct']:.2f} dB/oct"),
        ("L-R correlation / width", f"{m['stereo']['correlation']:.3f} / {m['stereo']['side_minus_mid_db']:.2f} dB (S-M)"),
    ]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in rows)
    return f"<table class='metrics'>{trs}</table>"


def checks_list(rec):
    out = []
    for c in rec["checks"]:
        col = BADGE[c["status"]][0]
        out.append(f"<li><span style='color:{col};font-weight:700'>{c['status']}</span> "
                   f"{c['check']} — measured <code>{c['measured']}</code> "
                   f"expected <code>{c['expected']}</code> "
                   f"<span class='muted'>{c['note']}</span></li>")
    return "<ul class='checks'>" + "".join(out) + "</ul>"


def main():
    REP.mkdir(parents=True, exist_ok=True)
    summary = json.loads((VAL / "summary.json").read_text(encoding="utf-8"))
    recs = {}
    for fn in sigreg.SIGNALS:
        p = VAL / f"{Path(fn).stem}.json"
        if p.exists():
            recs[fn] = json.loads(p.read_text(encoding="utf-8"))

    # charts keyed by signal file
    charts = {
        "pink_noise_minus20.wav": [chart_pink_overlay(), chart_bands(recs["pink_noise_minus20.wav"])],
        "sine_sweep_minus20.wav": [chart_sweep()],
        "click_track.wav": [chart_click()],
        "tone_ladder_minus20.wav": [chart_tone(recs["tone_ladder_minus20.wav"])],
        "dynamic_test_minus14.wav": [chart_dynamic(recs["dynamic_test_minus14.wav"])],
        "mid_side_test_minus20.wav": [chart_midside(recs["mid_side_test_minus20.wav"])],
    }

    ov = summary["overall_status"]
    sumrows = "".join(
        f"<tr><td>{badge(r['status'])}</td><td><b>{r['file']}</b></td>"
        f"<td>{r['role']}</td><td class='num'>{r['n_checks']}</td>"
        f"<td class='num'>{r['n_fail']}</td><td class='num'>{r['n_warn']}</td></tr>"
        for r in summary["signals"])

    sections = []
    for fn in sigreg.SIGNALS:
        if fn not in recs:
            continue
        r = recs[fn]
        imgs = "".join(f"<img src='data:image/png;base64,{c}'/>" for c in charts.get(fn, []))
        sections.append(f"""
        <section>
          <h3>{badge(r['status'])} &nbsp; {fn} <span class='muted'>· {r['role']}</span></h3>
          <p class='purpose'>{r['purpose']}</p>
          <div class='grid'>{metrics_table(r)}<div class='charts'>{imgs}</div></div>
          <details><summary>{len(r['checks'])} checks</summary>{checks_list(r)}</details>
        </section>""")

    meth = "".join(f"<li><b>{k}:</b> {v}</li>" for k, v in summary["methodology"].items())
    env = summary["environment"]
    envline = " · ".join(f"{k} {v}" for k, v in env.items())

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Test-Signal Validation Report</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:24px auto;
   color:#1f2937;padding:0 18px;line-height:1.45}}
 h1{{margin-bottom:2px}} h3{{border-top:1px solid #e5e7eb;padding-top:16px;margin-top:26px}}
 .muted{{color:#6b7280;font-weight:400;font-size:13px}}
 .purpose{{color:#374151;font-style:italic;margin:2px 0 10px}}
 table{{border-collapse:collapse;width:100%}}
 .summary td,.summary th{{border:1px solid #e5e7eb;padding:6px 9px;text-align:left}}
 .summary th{{background:#f3f4f6}}
 .metrics td{{padding:3px 8px;border-bottom:1px solid #eee}}
 .metrics td:first-child{{color:#4b5563}}
 .num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace}}
 .grid{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}
 .metrics{{flex:0 0 360px}} .charts{{flex:1;min-width:320px}}
 img{{max-width:100%;border:1px solid #e5e7eb;border-radius:6px;margin:6px 0;background:#fff}}
 code{{background:#f3f4f6;padding:1px 5px;border-radius:3px;font-size:12px}}
 details{{margin-top:8px}} summary{{cursor:pointer;color:#2563eb}}
 ul.checks{{font-size:13px}} .meth{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px}}
 .hero{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;margin:14px 0}}
</style></head><body>
<h1>Test-Signal Validation Report</h1>
<p class='muted'>Generated {summary['generated_utc']} · {summary['n_signals']} signals · overall {badge(ov)}</p>
<div class='hero'>
  <b>What this is.</b> Calibration pass over the 8 spectrally-neutral test signals that anchor every
  preset fingerprint. Each signal is measured and asserted against ground truth confirmed from the
  committed WAVs themselves. All-PASS means the measurement instrument is trustworthy before any
  mastering-service data is introduced.
</div>
<table class='summary'>
 <tr><th>Status</th><th>Signal</th><th>Role</th><th>Checks</th><th>Fail</th><th>Warn</th></tr>
 {sumrows}
</table>
<h2>Per-signal detail</h2>
{''.join(sections)}
<h2>Methodology</h2>
<div class='meth'><ul>{meth}</ul>
<p class='muted'>Environment: {envline}</p></div>
</body></html>"""

    out_html = REP / "validation-report.html"
    out_html.write_text(html, encoding="utf-8", newline="\n")

    # markdown summary
    md = [f"# Test-Signal Validation — {ov}",
          f"_Generated {summary['generated_utc']}_\n",
          "| Status | Signal | Role | Checks | Fail | Warn |",
          "|---|---|---|---|---|---|"]
    for r in summary["signals"]:
        md.append(f"| {r['status']} | {r['file']} | {r['role']} | {r['n_checks']} | {r['n_fail']} | {r['n_warn']} |")
    md.append("\n## Key measured values\n")
    for fn, r in recs.items():
        m = r["measurement"]
        md.append(f"- **{fn}** — RMS {m['levels']['rms_dbfs']:.2f} dBFS · "
                  f"{m['loudness']['integrated_lufs']:.2f} LUFS · "
                  f"slope {m['spectral']['slope_db_per_oct']:.2f} dB/oct · "
                  f"corr {m['stereo']['correlation']:.3f}")
    (REP / "validation-summary.md").write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"Wrote {out_html.relative_to(ROOT)}")
    print(f"Wrote {(REP / 'validation-summary.md').relative_to(ROOT)}")
    print(f"HTML size: {out_html.stat().st_size/1024:.0f} KB (charts embedded)")


if __name__ == "__main__":
    main()
