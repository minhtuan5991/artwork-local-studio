param([switch]$Installer)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = "python" }
$version = & $pythonPath -c "from artwork_local import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0) { throw "Cannot read version" }
$version = $version.Trim()
$releaseBase = Join-Path $projectRoot "release\$version"
$releaseRoot = Join-Path $releaseBase "ArtworkLocalStudio"
$versionFile = Join-Path $projectRoot "build\version-info.txt"
$iconFile = Join-Path $projectRoot "assets\app.ico"
& $pythonPath tools/build_assets.py
if ($LASTEXITCODE -ne 0) { throw "Asset build failed" }
& $pythonPath tools/version_info.py
if ($LASTEXITCODE -ne 0) { throw "Version metadata failed" }
& $pythonPath -m PyInstaller --noconfirm --clean --onedir --windowed --name ArtworkLocalStudio --icon $iconFile --version-file $versionFile --distpath $releaseBase --workpath "build/$version/gui" --specpath build main.py
if ($LASTEXITCODE -ne 0) { throw "GUI build failed" }
& $pythonPath -m PyInstaller --noconfirm --clean --onedir --console --name ArtworkNativeHost --icon $iconFile --version-file $versionFile --distpath "build/$version/host" --workpath "build/$version/native" --specpath build native_main.py
if ($LASTEXITCODE -ne 0) { throw "Native host build failed" }
Copy-Item -LiteralPath "build\$version\host\ArtworkNativeHost\ArtworkNativeHost.exe" -Destination $releaseRoot -Force
Copy-Item -LiteralPath "build\$version\host\ArtworkNativeHost\_internal" -Destination $releaseRoot -Recurse -Force
foreach ($name in @("model-manifest.json","browser-extension","README-VI.md","docs","licenses","assets")) {
    Copy-Item -LiteralPath $name -Destination $releaseRoot -Recurse -Force
}
& $pythonPath tools/configure_release.py $releaseRoot
if ($LASTEXITCODE -ne 0) { throw "Release setup failed" }
& $pythonPath tools/package_release.py
if ($LASTEXITCODE -ne 0) { throw "Portable ZIP failed" }
if ($Installer) {
    $compiler = Join-Path $projectRoot ".tools\inno\ISCC.exe"
    if (-not (Test-Path -LiteralPath $compiler)) {
        & $pythonPath tools/bootstrap_dev.py
        if ($LASTEXITCODE -ne 0) { throw "Build tools unavailable" }
    }
    & $compiler "/DAppVersion=$version" "/DSourceDir=$releaseRoot" "/DOutputDir=$releaseBase" "installer\ArtworkLocalStudio.iss"
    if ($LASTEXITCODE -ne 0) { throw "Installer compile failed" }
    & $pythonPath tools/release_checksums.py
    if ($LASTEXITCODE -ne 0) { throw "Checksum manifest failed" }
}
Write-Host "Ready: $releaseRoot\ArtworkLocalStudio.exe"
