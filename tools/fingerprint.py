"""
Step 3 of the method: measure the input->output delta for each test signal a
mastering service processed, and aggregate per-preset fingerprints.

The fingerprint of a preset is the set of static deltas it imposes on neutral
signals: tonal (EQ), loudness, dynamics, stereo, and limiting behavior.

Usage:
  .venv/Scripts/python tools/fingerprint.py                 # all services found
  .venv/Scripts/python tools/fingerprint.py --service bandlab
  .venv/Scripts/python tools/fingerprint.py --self-test     # synthetic sanity check

Input layout (operator drops files here):
  competitors/<service>/<preset>/<anything-with-source-stem>.wav
Outputs:
  measurements/fingerprints/<service>/<preset>/<signal>.json   per input/output pair
  measurements/fingerprints/<service>/<preset>/fingerprint.json aggregate per preset
  measurements/fingerprints/<service>/canonical.json            agent-canonical dataset
"""
from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import soundfile as sf

import audio_metrics as am
import signals as sigreg

SRC = ROOT / "source" / "test-signals"
COMP = ROOT / "competitors"
OUT = ROOT / "measurements" / "fingerprints"


# --------------------------------------------------------------------------- #
# Delta helpers
# --------------------------------------------------------------------------- #
def _sub(a, b):
    """out - in, tolerant of None/inf."""
    try:
        if a is None or b is None:
            return None
        d = float(a) - float(b)
        return None if not np.isfinite(d) else round(d, 3)
    except (TypeError, ValueError):
        return None


def band_deltas(in_rec, out_rec):
    ib = in_rec["spectral"]["bands_dbfs"]
    ob = out_rec["spectral"]["bands_dbfs"]
    raw = {k: _sub(ob[k], ib[k]) for k in ib}
    rms_delta = _sub(out_rec["levels"]["rms_dbfs"], in_rec["levels"]["rms_dbfs"])
    # Level-normalized = EQ *shape* independent of overall makeup gain.
    norm = {k: (round(v - rms_delta, 3) if v is not None and rms_delta is not None else None)
            for k, v in raw.items()}
    return raw, norm, rms_delta


def tone_gains(in_rec, out_rec):
    """Per-frequency gain (output - input level) at each ladder tone."""
    it = {t["expected_hz"]: t["level_dbfs"]
          for t in in_rec.get("signal_specific", {}).get("tones", []) if t["expected_hz"]}
    ot = {t["expected_hz"]: t["level_dbfs"]
          for t in out_rec.get("signal_specific", {}).get("tones", []) if t["expected_hz"]}
    return {f"{hz}Hz": _sub(ot.get(hz), it.get(hz)) for hz in sorted(it) if hz in ot}


def click_attack_release(path, period_sec=0.5):
    """
    Compressor/limiter timing from the processed click track: per-impulse
    transient peak and release time (peak -> -20 dB). Returns medians.
    """
    a = am.load_audio(path)
    mono = a["data"].mean(axis=1)
    sr = a["sample_rate"]
    env = np.abs(mono)
    # 1 ms moving-average envelope
    w = max(1, int(0.001 * sr))
    env_s = np.convolve(env, np.ones(w) / w, mode="same")
    period = int(period_sec * sr)
    n = len(mono) // period
    rel_times, peaks = [], []
    for k in range(1, n - 1):
        seg = env_s[k * period:(k + 1) * period]
        if seg.size == 0:
            continue
        pk_i = int(np.argmax(seg))
        pk = seg[pk_i]
        if pk <= 0:
            continue
        peaks.append(pk)
        thresh = pk * (10 ** (-20 / 20))  # -20 dB from peak
        tail = seg[pk_i:]
        below = np.where(tail < thresh)[0]
        if below.size:
            rel_times.append(below[0] / sr * 1000.0)
    return {
        "median_release_ms_to_-20dB": round(float(np.median(rel_times)), 2) if rel_times else None,
        "median_transient_peak_dbfs": round(am.db(np.median(peaks)), 2) if peaks else None,
        "n_impulses_analyzed": len(peaks),
    }


# --------------------------------------------------------------------------- #
# Single pair
# --------------------------------------------------------------------------- #
def fingerprint_pair(source_file, output_path):
    role = sigreg.role_for(source_file)
    in_rec = am.measure_file(SRC / source_file, role=role)
    out_rec = am.measure_file(output_path, role=role)

    raw_band, norm_band, rms_delta = band_deltas(in_rec, out_rec)
    delta = {
        "rms_db": rms_delta,
        "integrated_lufs": _sub(out_rec["loudness"]["integrated_lufs"], in_rec["loudness"]["integrated_lufs"]),
        "lra_lu": _sub(out_rec["loudness"]["lra_lu"], in_rec["loudness"]["lra_lu"]),
        "true_peak_dbtp": _sub(out_rec["levels"]["true_peak_dbtp"], in_rec["levels"]["true_peak_dbtp"]),
        "crest_factor_db": _sub(out_rec["levels"]["crest_factor_db"], in_rec["levels"]["crest_factor_db"]),
        "centroid_hz": _sub(out_rec["spectral"]["centroid_hz"], in_rec["spectral"]["centroid_hz"]),
        "slope_db_per_oct": _sub(out_rec["spectral"]["slope_db_per_oct"], in_rec["spectral"]["slope_db_per_oct"]),
        "correlation": _sub(out_rec["stereo"]["correlation"], in_rec["stereo"]["correlation"]),
        "side_minus_mid_db": _sub(out_rec["stereo"]["side_minus_mid_db"], in_rec["stereo"]["side_minus_mid_db"]),
        "band_energy_raw_db": raw_band,
        "band_energy_shape_db": norm_band,   # makeup-gain-removed EQ shape
    }
    if role == "tone_ladder":
        delta["tone_gain_db"] = tone_gains(in_rec, out_rec)
    if role == "dynamic":
        ic = in_rec["signal_specific"].get("contrast_db")
        oc = out_rec["signal_specific"].get("contrast_db")
        delta["dynamic_contrast_change_db"] = _sub(oc, ic)
    if role == "click_track":
        delta["limiter_timing"] = click_attack_release(output_path)

    dur_mismatch = abs(out_rec["format"]["duration_sec"] - in_rec["format"]["duration_sec"])
    return {
        "source_file": source_file,
        "output_file": Path(output_path).name,
        "role": role,
        "warnings": (["duration mismatch %.3fs - outputs assumed time-aligned"
                      % dur_mismatch] if dur_mismatch > 0.1 else []),
        "input": in_rec,
        "output": out_rec,
        "delta": delta,
    }


# --------------------------------------------------------------------------- #
# Aggregate a preset
# --------------------------------------------------------------------------- #
def aggregate_preset(pairs):
    """Roll per-signal deltas into a preset-level fingerprint with interpretation."""
    by_role = {p["role"]: p for p in pairs}
    fp = {"n_signals": len(pairs),
          "signals_present": sorted({p["source_file"] for p in pairs})}

    # Loudness target: prefer the -20 pink reference, else any pink, else mean.
    pink = next((p for p in pairs if p["source_file"] == "pink_noise_minus20.wav"),
                next((p for p in pairs if "pink" in p["source_file"]), None))
    if pink:
        fp["loudness"] = {
            "output_integrated_lufs": pink["output"]["loudness"]["integrated_lufs"],
            "makeup_gain_db": pink["delta"]["rms_db"],
            "true_peak_ceiling_dbtp": pink["output"]["levels"]["true_peak_dbtp"],
            "lra_change_lu": pink["delta"]["lra_lu"],
            "crest_change_db": pink["delta"]["crest_factor_db"],
        }
        # EQ shape from the primary pink reference (makeup-gain removed).
        fp["eq_shape_db"] = pink["delta"]["band_energy_shape_db"]
        fp["spectral_tilt_change_db_per_oct"] = pink["delta"]["slope_db_per_oct"]
        fp["centroid_shift_hz"] = pink["delta"]["centroid_hz"]

    if "tone_ladder" in by_role:
        fp["tone_gain_db"] = by_role["tone_ladder"]["delta"].get("tone_gain_db")
    if "dynamic" in by_role:
        fp["dynamics"] = {
            "contrast_change_db": by_role["dynamic"]["delta"].get("dynamic_contrast_change_db"),
            "note": "negative = preset compresses loud/quiet contrast",
        }
    if "mid_side" in by_role:
        d = by_role["mid_side"]["delta"]
        fp["stereo"] = {"correlation_change": d["correlation"],
                        "width_change_db": d["side_minus_mid_db"],
                        "note": "positive width_change = wider; correlation up = narrower"}
    if "click_track" in by_role:
        fp["limiter_timing"] = by_role["click_track"]["delta"].get("limiter_timing")

    # Level-dependence: compare makeup gain across pink levels if multiple present.
    pinks = {p["source_file"]: p["delta"]["rms_db"] for p in pairs if "pink" in p["source_file"]}
    if len(pinks) > 1:
        fp["level_dependence"] = {
            "makeup_gain_by_input_level": pinks,
            "note": "differing gains => level-dependent (adaptive) processing",
        }
    return fp


# --------------------------------------------------------------------------- #
# Capture provenance — the exact service settings each master was made under.
# Lives in competitors/<service>/capture.json (committed; audio is gitignored).
# --------------------------------------------------------------------------- #
def load_capture(service):
    p = COMP / service / "capture.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def capture_for_signal(capture, source_file, in_rec):
    """Attach the fixed protocol + this signal's recorded suggested input gain,
    and cross-check that suggestion against the service's auto-gain model."""
    if not capture:
        return None
    proto = capture.get("protocol", {})
    block = {"input_gain_db": proto.get("input_gain_db"),
             "intensity": proto.get("intensity")}
    rec = capture.get("per_signal", {}).get(source_file)
    if rec and rec.get("suggested_input_gain_db") is not None:
        sug = rec["suggested_input_gain_db"]
        block["suggested_input_gain_db"] = sug
        block["suggested_status"] = rec.get("status")
        # implied pre-chain peak target = input peak + suggested gain
        peak = in_rec["levels"]["peak_dbfs"]
        block["implied_target_peak_dbfs"] = round(peak + sug, 2)
    return block


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def process_service(service):
    sdir = COMP / service
    presets_out = {}
    if not sdir.exists():
        return None, f"no directory {sdir.relative_to(ROOT)}"
    capture = load_capture(service)
    preset_dirs = [d for d in sdir.iterdir() if d.is_dir()]
    for pdir in sorted(preset_dirs):
        wavs = sorted(pdir.glob("*.wav")) + sorted(pdir.glob("*.WAV"))
        pairs = []
        unmatched = []
        for w in wavs:
            src = sigreg.match_source(w.name)
            if src is None:
                unmatched.append(w.name)
                continue
            pair = fingerprint_pair(src, w)
            pair["capture"] = capture_for_signal(capture, src, pair["input"])
            pairs.append(pair)
        if not pairs:
            presets_out[pdir.name] = {"status": "empty", "unmatched": unmatched}
            continue
        out_pdir = OUT / service / pdir.name
        out_pdir.mkdir(parents=True, exist_ok=True)
        for p in pairs:
            (out_pdir / f"{Path(p['source_file']).stem}.json").write_text(
                json.dumps(p, indent=2), encoding="utf-8", newline="\n")
        fp = aggregate_preset(pairs)
        fp_doc = {"service": service, "preset": pdir.name,
                  "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "unmatched_files": unmatched, "fingerprint": fp}
        (out_pdir / "fingerprint.json").write_text(json.dumps(fp_doc, indent=2), encoding="utf-8", newline="\n")
        presets_out[pdir.name] = fp_doc
    return presets_out, None


def write_canonical(service, presets_out):
    sdir = OUT / service
    sdir.mkdir(parents=True, exist_ok=True)
    canonical = {
        "schema": "preset-fingerprint/v1",
        "service": service,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "Static-character isolation via spectrally-neutral test signals. "
                  "Delta = output measurement - input measurement. EQ shape is "
                  "makeup-gain-normalized band energy. See reports/ and tools/.",
        "capture_protocol": load_capture(service),
        "signal_provenance": {fn: {"role": s["role"], "purpose": s["purpose"]}
                              for fn, s in sigreg.SIGNALS.items()},
        "presets": {name: doc.get("fingerprint", doc) for name, doc in presets_out.items()},
    }
    (sdir / "canonical.json").write_text(json.dumps(canonical, indent=2), encoding="utf-8", newline="\n")
    return sdir / "canonical.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default=None, help="service name (dir under competitors/)")
    ap.add_argument("--self-test", action="store_true", help="run synthetic delta sanity check")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    services = ([args.service] if args.service
                else [d.name for d in COMP.iterdir() if d.is_dir()] if COMP.exists() else [])
    if not services:
        print("No competitor data found under competitors/. "
              "Drop outputs in competitors/<service>/<preset>/ and re-run.")
        return 0
    for svc in services:
        presets_out, err = process_service(svc)
        if err:
            print(f"[{svc}] {err}")
            continue
        n_done = sum(1 for v in presets_out.values() if "fingerprint" in v)
        print(f"[{svc}] fingerprinted {n_done}/{len(presets_out)} presets")
        for name, v in presets_out.items():
            if "fingerprint" in v:
                fp = v["fingerprint"]
                ld = fp.get("loudness", {})
                print(f"    {name:<12} {fp['n_signals']} signals · "
                      f"out {ld.get('output_integrated_lufs','?')} LUFS · "
                      f"makeup {ld.get('makeup_gain_db','?')} dB · "
                      f"tilt Δ {fp.get('spectral_tilt_change_db_per_oct','?')} dB/oct")
            else:
                print(f"    {name:<12} {v['status']} (unmatched: {v.get('unmatched')})")
        cpath = write_canonical(svc, presets_out)
        print(f"    canonical -> {cpath.relative_to(ROOT)}")
    return 0


# --------------------------------------------------------------------------- #
# Self-test: synthesize a 'mastered' pink file with a KNOWN transform and
# confirm the fingerprint recovers it.
# --------------------------------------------------------------------------- #
def self_test():
    import tempfile
    from scipy import signal as sps
    print("Self-test: apply known +8 dB makeup + high-shelf brightening to pink_noise_minus20")
    a = am.load_audio(SRC / "pink_noise_minus20.wav")
    x, sr = a["data"], a["sample_rate"]
    # high-shelf +6 dB above ~3 kHz via a simple 1st-order shelf
    b, aa = sps.butter(2, 3000 / (sr / 2), btype="high")
    hp = sps.filtfilt(b, aa, x, axis=0)
    shelf = x + (10 ** (6 / 20) - 1) * hp          # boost highs ~6 dB
    y = shelf * (10 ** (8 / 20))                     # +8 dB makeup
    y = np.clip(y, -1.0, 1.0)
    tmp = Path(tempfile.mkdtemp())
    (tmp).mkdir(exist_ok=True)
    outwav = tmp / "pink_noise_minus20_SELFTEST.wav"
    sf.write(outwav, y, sr, subtype="PCM_16")
    pair = fingerprint_pair("pink_noise_minus20.wav", outwav)
    d = pair["delta"]
    print(f"  recovered makeup gain (rms_db): {d['rms_db']:+.2f} dB   (injected +8 dB pre-clip)")
    print(f"  spectral tilt change:           {d['slope_db_per_oct']:+.2f} dB/oct (expect positive = brighter)")
    print(f"  centroid shift:                 {d['centroid_hz']:+.0f} Hz (expect positive)")
    print(f"  EQ shape (makeup-removed) by band:")
    for k, v in d["band_energy_shape_db"].items():
        bar = "#" * max(0, int((v + 2) * 3))
        print(f"    {k:<12} {v:+.2f} dB  {bar}")
    ok = (d["slope_db_per_oct"] > 0.3 and d["centroid_hz"] > 0
          and d["band_energy_shape_db"]["8-16k Hz"] > d["band_energy_shape_db"]["60-120 Hz"])
    print(f"\n  RESULT: {'PASS - delta math recovers the injected brightening' if ok else 'FAIL'}")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
