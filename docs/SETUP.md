# Set up the Overwatch scanner and restoration workflow

Both workflows use Python 3.11 or 3.12, NumPy, and OpenCV. From the repository root on Windows, create an environment and install the dependencies.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The [restoration workflow](RESTORATION.md) runs on folders of PNG frames. The [Overwatch scanner](OVERWATCH.md) also needs FFmpeg and ffprobe on PATH, Windows PowerShell 5.1, and the Windows English OCR language component. Get FFmpeg from the [official download page](https://ffmpeg.org/download.html). If the executables are outside PATH, set the FFMPEG and FFPROBE environment variables to their full paths.

To check the setup on synthetic footage and images, run the following from the repository root.

```powershell
$env:TEST_WINDOWS_OCR = '1'
python -m unittest discover -s tests -v
```
