# Konr Wings

[Download Konr Wings for Windows x64](https://raw.githubusercontent.com/yandleyick/candlestick-creator-toolkit/main/downloads/konr-wings.zip)

Extract the ZIP and double-click `Konr Wings.exe`. The wings appear at the center of the Overwatch window while it has focus on an LG monitor with hardware ID `GSM5CEC`. Switching away from the game hides the overlay. The two transparent PNGs in the ZIP can also be used on their own.

| Control | Action |
| --- | --- |
| Ctrl + Alt + W | Switch between Rainbow and Deep Black. |
| Ctrl + Alt + H | Hide or show the wings. |
| Konr Wings system tray icon | Choose **Deep Black** or **Rainbow** directly, or exit the overlay. |

Konr Wings remembers the last color you selected.

## Build from source

Run these commands in PowerShell from this directory with Zig 0.14.1 on your PATH and the .NET Framework C# compiler installed. The first two commands generate the texture and both PNGs. The last two build the Windows x64 executable.

```powershell
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /r:System.Drawing.dll MakeReticles.cs
.\MakeReticles.exe wings.rgba .
zig rc /fo overlay.res overlay.rc
zig c++ overlay.cpp overlay.res -target x86_64-windows-gnu -std=c++17 -O2 -s '-Wl,--subsystem,windows' -municode -ld3d11 -ldxgi -ldcomp -luuid -lole32 -lshell32 -ladvapi32 -luser32 -o 'Konr Wings.exe'
```
