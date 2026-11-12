# Setup on Windows

Keep this repository, large source recordings, and generated frames on a local work drive. Keep application/model installs outside the repository.

## Existing FMHY installation

The original toolkit lives at `D:\Tools\FMHy_Toolkit`. Its `toolkit.ps1` launcher and `evidence\tool-paths.json` remain the source of local executable paths. The repository does not replace that installation.

```powershell
pwsh -File scripts/toolkit.ps1 list
pwsh -File scripts/toolkit.ps1 ffmpeg -version
```

For a different installation, set `$env:TOOLKIT_ROOT` before using the bridge. This requires PowerShell 7 because the original launcher uses `ConvertFrom-Json -AsHashtable`.

## Python tools

Use Python 3.11 or 3.12 and a separate environment. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Only for transcription:
.\.venv\Scripts\python.exe -m pip install -r requirements-transcription.txt
```

Install FFmpeg from its [official download directory](https://ffmpeg.org/download.html) or reuse the FMHY installation. Set executable paths for this shell only:

```powershell
$paths = Get-Content 'D:\Tools\FMHy_Toolkit\evidence\tool-paths.json' -Raw | ConvertFrom-Json
$env:FFMPEG = $paths.ffmpeg
$env:FFPROBE = $paths.ffprobe
```

The examples below use `python`; substitute `.\.venv\Scripts\python.exe` when needed. CPU transcription is the default. CUDA transcription requires a compatible CTranslate2/CUDA/cuDNN setup; use the [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper) for the installed release. Model names may download model files on first use; a local model directory can also be passed.

The Overwatch OCR bridge uses Windows PowerShell 5.1 (`powershell.exe`), the Windows Runtime OCR API, and the English OCR language pack. It processes decoded video images, not the desktop. Do not substitute PowerShell 7 for that OCR subprocess.

## Recreating an application installation

`catalog/fmhy-package-lock.json` preserves the 2026-10-20 package versions, publisher URLs, and recorded hashes. These are historical receipts, not a claim that old versions are current or that every old URL still works. Use each tool's publisher page for current releases. Recheck hashes against the publisher before installing. Proprietary applications such as Ableton and Premiere need their own licenses.

No installer, model download, account login, upload, or system-wide configuration change runs automatically when this repository is opened.
