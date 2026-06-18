"""Audit the capture metadata: were ALL YES Master renders done at intensity 0.5 and
input gain 0, with full preset x signal coverage? Cheap consistency check on what the
render harness recorded (does not re-render)."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent

for setname in ["yesmaster", "yesmaster-loudness-parity"]:
    cap = json.loads((ROOT / "competitors" / setname / "capture.json").read_text(encoding="utf-8"))
    proto = cap["protocol"]
    renders = cap["renders"]
    print(f"=== {setname} ===")
    print(f"  protocol intensity   : {proto.get('intensity')}")
    print(f"  protocol input_gain  : {proto.get('input_gain_db')} dB")
    strengths = Counter(round(r.get("effective_adaptive_strength", -1), 4) for r in renders)
    gains = Counter(r.get("input_gain_db", proto.get("input_gain_db")) for r in renders)
    presets = sorted(set(r["preset"] for r in renders))
    signals = sorted(set(r["source_file"] for r in renders))
    print(f"  renders              : {len(renders)}  ({len(presets)} presets x {len(signals)} signals = {len(presets) * len(signals)})")
    print(f"  effective_strength   : {dict(strengths)}")
    print(f"  per-render input_gain : {dict(gains)}")
    bad = [r for r in renders if round(r.get('effective_adaptive_strength', -1), 4) != 0.5]
    print(f"  renders NOT at 0.5    : {len(bad)}" + (f"  -> {[(r['preset'], r['source_file']) for r in bad]}" if bad else "  (none)"))
    print()
