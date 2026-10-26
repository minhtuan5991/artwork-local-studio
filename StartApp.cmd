@echo off
cd /d "%~dp0"
if exist "release\0.2.2\ArtworkLocalStudio\ArtworkLocalStudio.exe" (
  if exist "release\0.2.2\ArtworkLocalStudio\data\studio.sqlite3" (
    start "" "release\0.2.2\ArtworkLocalStudio\ArtworkLocalStudio.exe"
  ) else if exist "release\0.2.1\ArtworkLocalStudio\data\studio.sqlite3" (
    start "" "release\0.2.2\ArtworkLocalStudio\ArtworkLocalStudio.exe" --data-dir "%~dp0release\0.2.1\ArtworkLocalStudio\data"
  ) else (
    start "" "release\0.2.2\ArtworkLocalStudio\ArtworkLocalStudio.exe"
  )
) else (
  ".venv\Scripts\pythonw.exe" main.py
)
