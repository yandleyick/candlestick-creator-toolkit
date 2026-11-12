# Finding moments in Overwatch footage

There are two different editorial tasks. Declare the intended task before scanning:

- **Own-POV Tracer streaks:** find several actual Tracer final blows in one life. The current candidate builder starts at three possible events. There is no arbitrary maximum spacing between kills; a 2+1 sequence can still be in the same life.
- **Enemy-Tracer / victim-POV encounters:** find an enemy Tracer producing the requested outcome, then judge how much of the meaningful encounter the POV followed. A POV killing the enemy Tracer is the opposite outcome and does not satisfy an enemy-Tracer lethal-highlight request.

The supplied automated scanner is tuned for the first task. The second task uses the same evidence/review discipline but needs separate outcome adjudication; do not present its output as an automated enemy-Tracer classifier.

## Source and timeline

Use locally available recordings. Record the VOD ID, original source link, source duration, local-file offset within the VOD, and any missing ranges. Downloading or cutting a range must not silently change the timestamp basis. Keep the original file and all review decisions.

The sampler decodes normally and records the selected frames' FFmpeg presentation timestamps. It does not use keyframes only or replace source timing with a made-up frame counter. The scanner retains decode logs and checks coverage and monotonic timestamps. Sampling can still miss events.

## Calibrate before the long scan

```powershell
python scripts/overwatch/sample_killfeed.py jobs/vod.mp4 --out jobs/calibration --start 600 --duration 30 --interval 0.5 --full-every 5
```

Review the frames at the normalized 1920x1080 scale. The included Tracer HUD/feed and name glyph images came from the original project. They are calibration examples, not universal templates. Different UI scale, compression, language, colors, streaming overlays, aspect ratio, or player aliases require new calibration. Do not stretch non-16:9 footage into this fixed geometry and trust its detections.

The basic sampler's default crop is 768x324 at x=1152,y=0; the full scanner uses the top-right 768x480 plus a separate lower-left HUD crop. Check both against your footage. `--source-offset` is the original VOD time corresponding to this local file's start.

## Scan and assemble candidate lives

```powershell
python scripts/overwatch/scan_killfeed.py jobs/vod.mp4 --source-id vod-001 --name CANDLESTICK --out jobs/scan-001 --interval 0.5
python scripts/overwatch/build_life_candidates.py jobs/scan-001
```

Pass comma-separated names only when the source really changes aliases. Similar names are not interchangeable: the script uses HUD observations and calibrated glyphs to reduce confusion. `--fast-name-gate` is optional and requires templates for every alias; begin with ordinary OCR. `--cuda` is optional NVDEC acceleration and needs a compatible FFmpeg build. Verify a short sample before using either optimization.

Outputs include every sampled OCR observation, potential events, potential death/phase boundaries, retained visual evidence, progress, and candidate lives. These outputs are **not confirmed kills**. The initial scanner also makes conservative groups around missing HUD evidence; `build_life_candidates.py` deliberately rebuilds lives without treating a mere gap in recognized Tracer HUD as a proven death.

## Review the whole life or encounter

Confirm the large killer name, the first hero portrait, the victim, and the outcome. Exclude assists, deployables, another POV, killcam/POTG replays counted twice, wrong heroes, and duplicated feed observations. Check for a missed own death, round transition, hero change, or alias switch through the entire interval. Resurrection/re-kill events can be merged by the scanner's nine-second deduplication logic; inspect them explicitly.

Make a clip manifest using `config/clips.example.json`, with actual local-file IN/OUT times and meaningful context before the first event and after the outcome. Use `scripts/review.py` to record decisions and `scripts/media.py export` to render accepted clips. Preserve uncertainty and reviewed exclusions instead of deleting the evidence.

For enemy-Tracer focus grading, judge the complete connected engagement. Sustained attention, crosshair placement, turning, and reacquisition matter. Do not trim away weak earlier attention merely to inflate the grade. Healing to full does not automatically start a new encounter. Keep encounter focus, overall suitability, duration, and outcome eligibility in separate fields. A deliberately accepted surprise Pulse or useful killcam can justify a keep without falsely raising the encounter's focus score. Only apply these exceptions when the project's requested editorial rules permit them.

## Coverage and delivery

Keep a coverage ledger with scanned ranges, reviewed ranges, gaps, rejected candidates and reasons, and source offsets. A successful decode is not proof that every event was detected. A reviewed handful of candidates is not a fully reviewed VOD. If parallel/chunked processing is used, preserve offsets and audit overlaps, duplicate events, deaths, and streaks crossing chunk boundaries before merging.

Review files at normal playback speed, refine exact boundaries, export to a new folder, and inspect the final encode. Do not automatically import, replace, or publish an editor timeline based only on scanner output.
