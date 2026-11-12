# Freestyle video editing workflow

## 1. Preserve and inventory the recordings

Keep originals in a read-only source folder. Assign stable source IDs, record the original URL when applicable, and store the file hash and metadata. Do not replace an original with an upscale, crop, or normalized version. Record which alternate file was actually used to render.

```powershell
python scripts/media.py probe jobs/source.mp4 --out jobs/source-probe.json
python scripts/media.py sheet jobs/source.mp4 --out jobs/overview.jpg --count 12
```

Inspect whether the file is music/performance footage, guest footage, facecam/IRL, or audio only. Establish performer attribution from labels, credits, the user's identification, or explicit self-identification. Similar-sounding voices are not sufficient to resolve an unknown performer. Keep unresolved entries marked unresolved.

## 2. Make a working transcript

```powershell
python scripts/media.py transcribe jobs/source.mp4 --model large-v3-turbo --device cuda --compute-type float16 --out jobs/transcript.json
python scripts/media.py candidates jobs/transcript.json --out jobs/candidates.json
```

The CPU alternative is `--model small --device cpu --compute-type int8`. Rap over music can confuse ASR and voice activity detection; VAD is off unless explicitly enabled. Check words against the recording, especially names, dense rhymes, ad-libs, and beat changes. Word times remain on the original local-file clock. If this file was cut from a longer recording, retain the original offset separately.

The candidate generator proposes non-overlapping 20–30 second windows near phrase boundaries. It does not rate rap quality, verify improvised performance, or identify the best passages. Candidate lengths are a starting format and can be changed during review for the actual project.

## 3. Review passages in context

```powershell
python scripts/review.py jobs/candidates.json --decisions jobs/reviewed-clips.json
```

Open the printed localhost address. Watch the setup, payoff, and neighboring phrases. Change IN/OUT to complete ideas; record the performer and attribution basis. Set accepted entries to `approved`. Keep uncertain entries pending. Save or download the decisions. The server exposes only sources explicitly listed in the manifest and binds to localhost.

For lyrical comparisons, evaluate complexity, depth, and connected development separately. A useful default is 30% / 30% / 40%; if accessibility is explicitly requested, use 25% / 25% / 35% / 15%. Establish the rubric before ranking. Scores are judgments, not measurements. Do not derive delivery, breath control, flow, or listening approval from a transcript alone. Do not claim an exhaustive best-of if some eligible recordings remain unreviewed.

## 4. Export and caption approved selections

The exporter requires every entry in the supplied manifest to be approved; save a selection manifest containing only the clips you intend to render. Each clip uses source-local seconds. It rejects duplicate IDs, invalid intervals, missing media, existing output directories, and HDR input that needs a deliberate color conversion.

```powershell
python scripts/media.py export jobs/approved-clips.json --out jobs/render-v1
python scripts/media.py captions jobs/transcript.json --start 100 --end 125 --out jobs/clip-001.srt
```

Audio-only input gets a neutral video background; design the final title card in your editor. The SRT is an editable working caption file. Confirm words and timing before publishing. Automatic subtitles are not verified lyrics.

## 5. Finish the edit

Use Resolve or Premiere for arrangement, beat alignment, typography, reframing, transitions, and deliberate effects. Keep a clean master before making social crops. Preserve faces and meaningful gesture/action when reframing; inspect every change of shot. For audio, preserve an untreated reference and review clipping, intelligibility, beat balance, and transitions by listening.

The older recovery workflow rebuilt saved Windows Video Editor cuts as FCP7 XML. Preserve original timing units, media paths, missing-media markers, and frame rates; do not claim a recovered timeline works until imported and played in the target editor. The portable handoff script here writes reviewed cut CSV/JSON, not a reconstruction of a specific old project.

## 6. Validate and publish deliberately

```powershell
python scripts/media.py qa jobs/render-v1/clip-001.mp4 --out jobs/clip-001-qa.json
python scripts/handoff.py jobs/approved-clips.json --out jobs/editor-handoff
```

The exporter also records SHA-256, metadata, duration checks, and a complete decode result for each clip. Review the rendered beginning/end, captions, aspect ratio, skin texture, motion, and audio. Uploading is separate; these scripts do not publish. After an upload, verify the platform's processed resolution and actual playback independently.
