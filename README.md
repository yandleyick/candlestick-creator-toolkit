# Candlestick Creator Toolkit

A practical library for freestyle video editing, Overwatch/Tracer moment discovery, audio work, restoration, and everyday creator tools.

This repository brings together the original FMHY toolkit and the reusable parts of the production workflows. Application installers, model weights, source recordings, private account data, and project-specific review decisions stay outside Git.

## Start here

- [Windows setup](docs/SETUP.md)
- [Freestyle editing](docs/FREESTYLE.md)
- [Finding Overwatch moments](docs/OVERWATCH.md)
- [Restoration and export quality](docs/RESTORATION.md)
- [Audio and eight-vocal layout](docs/AUDIO.md)
- [Source records and coverage](docs/PROVENANCE.md)
- [Script commands](scripts/README.md)
- [Verification results](verification/README.md)

## Tool catalog

87 entries: 27 selected applications, 2 private runtime packages, 14 existing tools, 28 saved web resources, and 16 additional tools/components. Some entries represent separate builds or components of the same tool.

Recorded versions and checks belong to the date listed. A saved bookmark means it was collected, not that it was fully tested. Presence on disk does not prove a successful workflow.

The complete structured catalog is [catalog/tools.json](catalog/tools.json). Download records and hashes are in [catalog/fmhy-package-lock.json](catalog/fmhy-package-lock.json).

### 3D

| Tool | Role | Collection |
|---|---|---|
| [Tripo CLI](https://www.tripo3d.ai/) | 3D asset generation workflow | Additional production tools |

### Analysis

| Tool | Role | Collection |
|---|---|---|
| [OpenCV](https://opencv.org/) | Frame processing, calibrated glyph matching and contact sheets | Additional production tools |
| [NumPy](https://numpy.org/) | Audio arrays, image arrays and numerical processing | Additional production tools |
| [Pillow](https://python-pillow.github.io/) | Poster images and contact sheets | Additional production tools |
| [Windows OCR](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine) | English OCR of decoded killfeed and HUD images | Additional production tools |
| [ffprobe](https://ffmpeg.org/ffprobe.html) | Stream metadata, duration, frame counts and color metadata | Additional production tools |

### Audio

| Tool | Role | Collection |
|---|---|---|
| [Audacity](https://github.com/audacity/audacity/releases/tag/Audacity-4.0.1) | Waveform editing, recording and audio cleanup | FMHY toolkit selection |
| [fre:ac](https://github.com/enzo1982/freac/releases/tag/v1.1.7) | Batch audio conversion and tagging | FMHY toolkit selection |
| [Equalizer APO](https://sourceforge.net/projects/equalizerapo/) | Existing system audio configuration | Existing toolkit |
| [AudioSep environment](https://github.com/Audio-AGI/AudioSep) | Existing isolated audio-separation environment; models and inference not retested | Existing toolkit |
| [Tunebat](https://tunebat.com/) | Reference BPM and key lookup; not proof of a recording's key | Saved web resource |
| [Tone Generator](https://www.szynalski.com/tone-generator/) | Browser test tone generator | Saved web resource |
| [MusicKit](https://musickit.jull.dev/) | Browser metronome and musician utilities | Saved web resource |
| [Hydrogenaudio Knowledgebase](https://wiki.hydrogenaudio.org/) | Audio format and encoding reference | Saved web resource |
| [Ableton Live](https://www.ableton.com/live/) | Eight-layer vocal sessions and separate beat/music track | Additional production tools |
| [Shure MOTIV Mix](https://www.shure.com/en-US/products/software/motiv-mix) | Microphone recording and input setup | Additional production tools |

### Dependency

| Tool | Role | Collection |
|---|---|---|
| [.NET Desktop private runtime](https://dotnet.microsoft.com/download/dotnet/10.0) | Private runtime for CapFrameX; no system-wide runtime installation | FMHY toolkit selection |
| [.NET private host and core runtime](https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/10.0/releases.json) | Companion host for the private Desktop runtime used by CapFrameX | FMHY toolkit selection |

### Developer

| Tool | Role | Collection |
|---|---|---|
| [jq](https://github.com/jqlang/jq/releases/tag/jq-1.8.2) | Read, filter and transform JSON | FMHY toolkit selection |
| [fd](https://github.com/sharkdp/fd/releases/tag/v10.5.0) | Fast file discovery | FMHY toolkit selection |
| [uv](https://github.com/astral-sh/uv/releases/tag/0.13.4) | Manage isolated Python project environments | FMHY toolkit selection |
| [Deno](https://github.com/denoland/deno/releases/tag/v2.9.7) | JavaScript runtime used by yt-dlp and standalone tools | FMHY toolkit selection |
| [Visual Studio Code](https://code.visualstudio.com/) | Portable code editor with isolated settings and extensions | FMHY toolkit selection |
| [Git](https://git-scm.com/) | Existing bundled version-control tool | Existing toolkit |
| [Node.js](https://nodejs.org/) | Existing bundled JavaScript runtime | Existing toolkit |
| [Python](https://www.python.org/) | Existing bundled Python runtime | Existing toolkit |
| [DevDocs](https://devdocs.io/) | Searchable programming documentation | Saved web resource |
| [Can I Use?](https://caniuse.com/) | Browser feature compatibility | Saved web resource |
| [regex101](https://regex101.com/) | Regular expression testing | Saved web resource |
| [CodePen](https://codepen.io/) | Browser code experiments | Saved web resource |
| [CyberChef](https://gchq.github.io/CyberChef/) | Data encoding and transformation workbench | Saved web resource |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | Fast source and evidence searches | Additional production tools |

### Education

| Tool | Role | Collection |
|---|---|---|
| [Qalculate](https://github.com/Qalculate/qalculate-gtk/releases/tag/v5.13.0) | Local calculator, unit conversion and equations | FMHY toolkit selection |
| [Desmos](https://www.desmos.com/) | Interactive graphing | Saved web resource |
| [GeoGebra](https://www.geogebra.org/) | Geometry and math visualization | Saved web resource |
| [Wolfram Alpha](https://www.wolframalpha.com/) | Computational reference | Saved web resource |
| [ZoteroBib](https://zbib.org/) | Bibliographies without installing a research library | Saved web resource |
| [ResearchRabbit](https://www.researchrabbit.ai/) | Research literature discovery; account may be required | Saved web resource |
| [Wiktionary](https://www.wiktionary.org/) | Dictionary and language reference | Saved web resource |

### Files

| Tool | Role | Collection |
|---|---|---|
| [PeaZip](https://github.com/peazip/PeaZip/releases/tag/11.4.0) | Archive manager with bundled 7-Zip command line tools | FMHY toolkit selection |
| [LocalSend](https://github.com/localsend/localsend/releases/tag/v1.18.2) | Transfer files between devices on a local network | FMHY toolkit selection |
| [Czkawka CLI](https://github.com/qarmin/czkawka/releases/tag/12.0.2) | Find duplicate files; deletion requires a separately reviewed selection | FMHY toolkit selection |
| [rclone](https://github.com/rclone/rclone/releases/tag/v1.75.2) | Copy and verify cloud files when explicitly configured | FMHY toolkit selection |
| [Everything](https://www.voidtools.com/downloads/) | Fast filename search; portable copy with no service or startup installation | FMHY toolkit selection |
| [qpdf](https://github.com/qpdf/qpdf/releases/tag/v12.4.2) | Local PDF inspection, merging, splitting and repair; complementary command line utility | FMHY toolkit selection |

### Gaming

| Tool | Role | Collection |
|---|---|---|
| [PresentMon](https://github.com/GameTechDev/PresentMon/releases/tag/v2.6.0) | Frame-time measurement command line tool; no tuning applied | FMHY toolkit selection |
| [CapFrameX](https://www.capframex.com/download) | Game performance capture and analysis; prepared without changing game settings | FMHY toolkit selection |
| [MSI Afterburner](https://www.msi.com/Landing/afterburner/graphics-cards) | Existing hardware monitoring and tuning | Existing toolkit |
| [HWMonitor](https://www.cpuid.com/softwares/hwmonitor.html) | Existing hardware monitoring | Existing toolkit |
| [Backloggd](https://www.backloggd.com/) | Game backlog and personal tracking | Saved web resource |
| [OpenCritic](https://opencritic.com/) | Game review aggregation | Saved web resource |
| [IGDB](https://www.igdb.com/) | Game metadata lookup | Saved web resource |
| [SteamDB Ratings](https://steamdb.info/stats/gameratings/) | Steam rating and game lookup | Saved web resource |
| [DoesItPlay?](https://www.doesitplay.org/) | Offline play and preservation compatibility lookup | Saved web resource |

### Images

| Tool | Role | Collection |
|---|---|---|
| [ImageMagick](https://github.com/ImageMagick/ImageMagick/releases/tag/7.1.2-34) | Batch image conversion, resizing and contact sheets | FMHY toolkit selection |
| [Krita](https://krita.org/en/download/) | Layered image editing, painting, masks and animation | FMHY toolkit selection |
| [Inkscape](https://inkscape.org/) | Vector graphics, SVG artwork, titles and logos | FMHY toolkit selection |
| [ExifTool](https://exiftool.org/) | Inspect camera metadata and dates; metadata writes only when requested | FMHY toolkit selection |
| [Photopea](https://www.photopea.com/) | Browser image editor for layered files and quick edits | Saved web resource |
| [Squoosh](https://squoosh.app/) | Interactive image compression and format comparison | Saved web resource |
| [Coolors](https://coolors.co/) | Palette exploration | Saved web resource |
| [Excalidraw](https://excalidraw.com/) | Sketch diagrams and plans | Saved web resource |

### Internet

| Tool | Role | Collection |
|---|---|---|
| [aria2](https://github.com/aria2/aria2/releases/tag/release-1.37.0) | Resumable command line downloads | FMHY toolkit selection |
| [croc](https://github.com/schollz/croc/releases/tag/v11.5.5) | Code-based file transfer when explicitly requested | FMHY toolkit selection |
| [curl](https://curl.se/) | Built-in HTTP transfer client | Existing toolkit |
| [OpenSSH](https://github.com/PowerShell/Win32-OpenSSH) | Built-in secure shell client | Existing toolkit |
| [Cloudflare Speed Test](https://speed.cloudflare.com/) | Interactive connection measurements | Saved web resource |
| [fast](https://fast.com/) | Quick connection speed check | Saved web resource |
| [GlobalPing](https://globalping.io/) | Network reachability checks | Saved web resource |
| [MxToolbox](https://mxtoolbox.com/) | DNS and mail diagnostics | Saved web resource |

### Restoration

| Tool | Role | Collection |
|---|---|---|
| [NAFNet](https://github.com/megvii-research/NAFNet) | Neural deblurring experiments | Additional production tools |
| [Restormer](https://github.com/swz30/Restormer) | Motion and defocus deblurring experiments | Additional production tools |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Upscaling and restoration experiments | Additional production tools |
| [RIFE PyTorch](https://github.com/hzwer/ECCV2022-RIFE) | Frame interpolation using local RIFE model files | Additional production tools |

### Transcription

| Tool | Role | Collection |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local working transcripts with word timestamps | Additional production tools |

### Video

| Tool | Role | Collection |
|---|---|---|
| [LosslessCut](https://github.com/mifi/lossless-cut/releases/tag/v3.70.1) | Fast trimming and remuxing without re-encoding | FMHY toolkit selection |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.08.19) | Download source media when access and use are authorized | FMHY toolkit selection |
| [Subtitle Edit](https://github.com/SubtitleEdit/subtitleedit/releases/tag/v5.3.0) | Create, align and repair subtitles | FMHY toolkit selection |
| [MediaInfo CLI](https://mediaarea.net/en/MediaInfo) | Detailed media metadata and technical inspection | FMHY toolkit selection |
| [FFmpeg + ffprobe + ffplay](https://www.gyan.dev/ffmpeg/builds/) | Current full video/audio conversion and inspection suite; older project binaries preserved | FMHY toolkit selection |
| [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) | Timeline editing and finishing | Existing toolkit |
| [OBS Studio](https://obsproject.com/) | Existing recording workflow | Existing toolkit |
| [VLC](https://www.videolan.org/vlc/) | Playback | Existing toolkit |
| [RIFE](https://github.com/nihui/rife-ncnn-vulkan) | Existing project-specific interpolation binary | Existing toolkit |
| [Legacy FFmpeg](https://ffmpeg.org/) | Preserved for reproducible older projects | Existing toolkit |
| [Adobe Premiere Pro](https://www.adobe.com/products/premiere.html) | Recovered edit timelines and final video editing | Additional production tools |
| [Mosh-Pro](https://moshpro.app/) | Glitch and datamosh effects | Additional production tools |

## Operating principles

Keep original media. Keep source timestamps. Preserve review notes. Treat automatic transcripts and detection results as candidates. Confirm player/performer attribution and complete clip boundaries before final export. Technical checks and creative approval are separate.

## Sources

[FMHY](https://fmhy.net/) supplied the discovery catalog. Each entry links to its recorded FMHY section or publisher. This is a personal selection, not an official FMHY project or a mirror of the full directory. Third-party tools retain their own licenses; this repository does not relicense them.
