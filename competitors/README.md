# competitors/ — mastered output drop zone

Drop downloaded mastered WAVs here, organized by service and preset:

```
competitors/<service>/<preset>/<file>.wav
e.g.  competitors/bandlab/oomph/pink_noise_minus20_master.wav
```

**Audio files in here are gitignored** — only their measurements (under
`measurements/fingerprints/`) get committed.

## Naming

Keep the **source signal filename as a substring** so the fingerprint engine
auto-matches output→input. Any suffix the service adds is fine:

| Source signal | A valid dropped name |
|---|---|
| `pink_noise_minus20.wav` | `pink_noise_minus20_BandLab_Oomph.wav` |
| `tone_ladder_minus20.wav` | `tone_ladder_minus20-mastered.wav` |

Files that don't contain a known source stem are reported as `unmatched`
(never guessed). Rename them or note the mapping.

## BandLab presets expected

`universal/` · `clarity/` · `oomph/` · `tape/`

After dropping files: `.venv/Scripts/python tools/fingerprint.py --service bandlab`
