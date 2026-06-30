# Build ITIAS Coder for Windows (run on windows-latest or local Windows)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==> Installing build dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

Write-Host "==> Downloading ffmpeg (Windows essentials)"
$FfmpegDir = Join-Path $ProjectRoot "packaging" "ffmpeg-win"
$FfmpegZip = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
$FfmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if (-not (Test-Path (Join-Path $FfmpegDir "bin" "ffmpeg.exe"))) {
    New-Item -ItemType Directory -Force -Path $FfmpegDir | Out-Null
    Invoke-WebRequest -Uri $FfmpegUrl -OutFile $FfmpegZip
    Expand-Archive -Path $FfmpegZip -DestinationPath $FfmpegDir -Force
}

$FfmpegBin = Get-ChildItem -Path $FfmpegDir -Recurse -Filter "ffmpeg.exe" |
    Select-Object -First 1 -ExpandProperty DirectoryName
if (-not $FfmpegBin) {
    throw "ffmpeg.exe not found after extract"
}

Write-Host "==> Running PyInstaller"
python -m PyInstaller packaging/itias-coder.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$DistDir = Join-Path $ProjectRoot "dist" "ITIAS-Coder"
if (-not (Test-Path (Join-Path $DistDir "ITIAS-Coder.exe"))) {
    throw "Expected ITIAS-Coder.exe not found in $DistDir"
}
$BundledFfmpeg = Join-Path $DistDir "ffmpeg"
New-Item -ItemType Directory -Force -Path $BundledFfmpeg | Out-Null
Copy-Item (Join-Path $FfmpegBin "ffmpeg.exe") $BundledFfmpeg -Force
Copy-Item (Join-Path $FfmpegBin "ffprobe.exe") $BundledFfmpeg -Force

$Version = "0.1.0"
$ZipName = "ITIAS-Coder-v$Version-win64.zip"
$ZipPath = Join-Path $ProjectRoot "dist" $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $DistDir -DestinationPath $ZipPath -Force

Write-Host "==> Done: $ZipPath"
Get-Item $ZipPath | Format-List Name, Length, FullName
