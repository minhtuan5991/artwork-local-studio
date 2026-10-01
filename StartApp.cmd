@echo off
cd /d "%~dp0"
if exist "release\0.2.1\ArtworkLocalStudio\ArtworkLocalStudio.exe" (
  start "" "release\0.2.1\ArtworkLocalStudio\ArtworkLocalStudio.exe"
) else (
  ".venv\Scripts\pythonw.exe" main.py
)
