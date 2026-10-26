@echo off
cd /d "%~dp0"
if exist "ArtworkLocalStudio.exe" (
  start "" "%~dp0ArtworkLocalStudio.exe"
) else if exist "release\0.2.3\ArtworkLocalStudio\ArtworkLocalStudio.exe" (
  start "" "release\0.2.3\ArtworkLocalStudio\ArtworkLocalStudio.exe" --data-dir "%~dp0data"
) else (
  ".venv\Scripts\pythonw.exe" main.py
)
