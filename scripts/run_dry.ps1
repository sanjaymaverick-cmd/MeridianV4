# Offline dry demo. No broker. No OpenAlgo.
$ErrorActionPreference = "Stop"
if (-not $env:MERIDIAN_ROOT) { $env:MERIDIAN_ROOT = (Resolve-Path "$PSScriptRoot\..").Path }
$env:MERIDIAN_MODE = "dry"
Set-Location $env:MERIDIAN_ROOT
python src/openalgo/strategy_v4.py
