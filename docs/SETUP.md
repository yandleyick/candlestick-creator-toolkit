# Set up the creator workflows on Windows

Use Python 3.11 or 3.12. From the repository root on Windows, create an environment and install the dependencies.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The [freestyle editor](FREESTYLE.md) and [Overwatch scanner](OVERWATCH.md) use FFmpeg and ffprobe. Put both on PATH or set the FFMPEG and FFPROBE environment variables to their full paths. [FFmpeg downloads](https://ffmpeg.org/download.html)

For automatic transcription in the freestyle editor, run `python -m pip install -r requirements-transcription.txt` in the activated environment. The first transcription downloads the selected speech model unless you supply a local model directory. You can also start with a clip manifest and go straight to review and export.

The Overwatch scanner additionally needs Windows PowerShell 5.1 and the Windows English OCR language component. The [restoration workflow](RESTORATION.md) reads folders of PNG frames.

To check the setup on synthetic footage and images, run the following from the repository root.

```powershell
$env:TEST_WINDOWS_OCR = '1'
python -m unittest discover -s tests -v
```
