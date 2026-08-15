# Paper loop. Requires OpenAlgo running + Analyzer ON + API key in env (not in repo).
$ErrorActionPreference = "Stop"
if (-not $env:MERIDIAN_ROOT) { $env:MERIDIAN_ROOT = (Resolve-Path "$PSScriptRoot\..").Path }
if (-not $env:OPENALGO_API_KEY) { throw "Set OPENALGO_API_KEY" }
$env:MERIDIAN_MODE = "paper"
$env:MERIDIAN_LOOP = "1"
Set-Location $env:MERIDIAN_ROOT
python src/openalgo/strategy_v4.py
