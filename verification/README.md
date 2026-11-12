# Packaging verification — 2026-11-11

Ten automated tests passed on Windows with Python 3.12, the existing FFmpeg 9.0.2 build, OpenCV 5.0.0, and the Windows English OCR component. Runtime: 3.884 seconds. The tests use generated audio/video/images and invented transcript/events; no source recordings or real transcripts are distributed.

| Area | Exercised |
|---|---|
| Inventory | Unique catalog IDs, HTTPS publisher links, Python syntax |
| Selection | Pending selections, non-finite/reversed times, unsafe output IDs rejected |
| Transcripts | Candidate duration/non-overlap and clip-relative caption timing |
| Export | Actual synthetic audio/video encoding, full decode, duration, original hash preservation, overwrite rejection |
| Audio-only input | Video backdrop export and contact-sheet generation |
| Review service | HTTP catalog, byte-range media serving, unknown paths, request-origin checking, saved decisions |
| Overwatch grouping | Widely spaced kills remain in one life; an intervening death splits the group |
| Sampler | Sequential selected-frame PTS with nonzero seek and original-source offset |
| OCR pipeline | Windows OCR initialized and processed four blank-video samples without OCR errors or false kill observations |
| Restoration | 8-bit portrait and 16-bit landscape frames retain dimensions/depth and original pixels; repeated output refused |

PowerShell scripts passed AST parsing. The review page's embedded JavaScript passed `node --check`.

This verifies the listed operations, not real-footage detection accuracy or creative quality. The review page was not visually tested in a browser during this packaging run. Transcription models, GPU inference, CUDA decoding, NLE imports, and a clean-environment dependency installation were not exercised. Dependencies are bounded requirements, not a fully pinned environment lock.

## Run the checks

Set `FFMPEG` and `FFPROBE` to installed executables and install the base requirements, then run:

```powershell
python -m unittest discover -s tests -v
```

To include the optional Windows OCR integration test:

```powershell
$env:TEST_WINDOWS_OCR = '1'
python -m unittest discover -s tests -v
```

OpenCV/FFmpeg tests are skipped when their dependencies are unavailable. The OCR integration test is skipped unless explicitly enabled on Windows. Inspect the summary for skipped tests before comparing results.

## Publisher links

The [link-check report](link-check.json) records HEAD requests to all 87 catalog entries: 79 reachable and eight needing manual checking. A failed request can mean bot protection, rate limits, redirects, or unsupported HEAD requests; it does not by itself establish that a site is down. Reachability does not verify a download's safety or current functionality.
