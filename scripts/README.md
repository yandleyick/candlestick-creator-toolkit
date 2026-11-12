# Commands

Run from the repository root. Set `FFMPEG` and `FFPROBE` to executable paths or place them on PATH. Source files are preserved. Generated output belongs in an ignored `jobs/` directory.

| Command | Result |
|---|---|
| `python scripts/media.py probe INPUT --out probe.json` | Stream/container metadata |
| `python scripts/media.py qa INPUT --out qa.json` | Full decode, SHA-256, size, and metadata |
| `python scripts/media.py sheet INPUT --out sheet.jpg` | Overview contact sheet; seek labels are approximate |
| `python scripts/media.py transcribe INPUT --out transcript.json` | Automatic transcript with words and times |
| `python scripts/media.py candidates TRANSCRIPT --out candidates.json` | Unreviewed 20–30 second phrase candidates |
| `python scripts/review.py MANIFEST --decisions reviewed.json` | Local player and explicit cut/attribution decisions |
| `python scripts/media.py captions TRANSCRIPT --start 10 --end 35 --out clip.srt` | Editable captions relative to the chosen interval |
| `python scripts/media.py export APPROVED_MANIFEST --out NEW_FOLDER` | SDR clips with per-clip decode/duration/hash checks |
| `python scripts/handoff.py APPROVED_MANIFEST --out NEW_FOLDER` | Reviewed source-local cut CSV and JSON |
| `python scripts/restore_frames.py FRAMES --out NEW_FOLDER --mode gentle` | Bounded luminance recovery on PNG frames |
| `python scripts/overwatch/sample_killfeed.py INPUT --out NEW_FOLDER` | Timestamped calibration/evidence frames |
| `python scripts/overwatch/scan_killfeed.py INPUT --source-id ID --name NAME --out NEW_FOLDER` | Unverified OCR/CV events and coverage |
| `python scripts/overwatch/build_life_candidates.py SCAN_FOLDER` | Provisional same-life candidate groups |
| `pwsh -File scripts/toolkit.ps1 list` | Bridge to an existing local FMHY installation |

Global `media.py` executable overrides go before the subcommand, for example `python scripts/media.py --ffmpeg PATH --ffprobe PATH qa INPUT --out qa.json`.

The review UI saves all statuses. Make a separate approved-only manifest before export/handoff; export rejects a pending/rejected row instead of silently selecting it. All IN/OUT values are seconds relative to the local source file. Save original VOD offsets separately. The review player does not hide the source context; pause-at-OUT is a convenience, and the full source remains seekable.

The scanner is Windows-specific and tuned to its documented 1080p layout. It has no generalized guarantee for other games, HUDs, aliases, or aspect ratios. Inspect its calibration and generated evidence before long runs.
