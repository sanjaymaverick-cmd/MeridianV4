# Offline unit tests. No network required.
$ErrorActionPreference = "Stop"
if (-not $env:MERIDIAN_ROOT) { $env:MERIDIAN_ROOT = (Resolve-Path "$PSScriptRoot\..").Path }
Set-Location $env:MERIDIAN_ROOT
python -m pytest tests
