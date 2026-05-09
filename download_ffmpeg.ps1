<#
.SYNOPSIS
    Download an LGPL build of ffmpeg/ffprobe and place the binaries in .\bin

.DESCRIPTION
    Pulls a Windows LGPL shared build from BtbN's nightly mirror
    (https://github.com/BtbN/FFmpeg-Builds/releases) and extracts only
    ffmpeg.exe and ffprobe.exe into the local bin\ directory.

    BtbN is preferred because they publish stable LGPL-shared builds. If you
    want to swap in gyan.dev's LGPL build instead, change $Url below.
#>

[CmdletBinding()]
param(
    [string]$Url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl-shared.zip",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$binDir  = Join-Path $root "bin"
$tmpDir  = Join-Path $root ".cache"
$zipPath = Join-Path $tmpDir "ffmpeg-lgpl.zip"
$extract = Join-Path $tmpDir "ffmpeg-extracted"

New-Item -ItemType Directory -Force -Path $binDir, $tmpDir | Out-Null

$ffmpeg  = Join-Path $binDir "ffmpeg.exe"
$ffprobe = Join-Path $binDir "ffprobe.exe"

if (-not $Force -and (Test-Path $ffmpeg) -and (Test-Path $ffprobe)) {
    Write-Host "[skip] bin\ffmpeg.exe and bin\ffprobe.exe already exist (use -Force to redownload)."
    exit 0
}

Write-Host "[1/3] Downloading $Url"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $Url -OutFile $zipPath -UseBasicParsing

Write-Host "[2/3] Extracting"
if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
Expand-Archive -Path $zipPath -DestinationPath $extract -Force

$srcFfmpeg  = Get-ChildItem -Path $extract -Recurse -Filter "ffmpeg.exe"  | Select-Object -First 1
$srcFfprobe = Get-ChildItem -Path $extract -Recurse -Filter "ffprobe.exe" | Select-Object -First 1

if (-not $srcFfmpeg -or -not $srcFfprobe) {
    throw "ffmpeg.exe or ffprobe.exe not found in archive contents at $extract"
}

Copy-Item -Path $srcFfmpeg.FullName  -Destination $ffmpeg  -Force
Copy-Item -Path $srcFfprobe.FullName -Destination $ffprobe -Force

# Try to grab the LGPL license text bundled with the archive, if present.
$srcLicense = Get-ChildItem -Path $extract -Recurse -Include LICENSE*, COPYING* -File `
    | Select-Object -First 1
if ($srcLicense) {
    $licenseDest = Join-Path $root "licenses\ffmpeg-LICENSE.txt"
    New-Item -ItemType Directory -Force -Path (Split-Path $licenseDest) | Out-Null
    Copy-Item -Path $srcLicense.FullName -Destination $licenseDest -Force
    Write-Host "[info] Updated licenses\ffmpeg-LICENSE.txt from archive"
}

Write-Host "[3/3] Done."
Write-Host "  $ffmpeg"
Write-Host "  $ffprobe"
