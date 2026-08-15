# Nightly retrain. Never force-promotes.
$ErrorActionPreference = "Stop"
if (-not $env:MERIDIAN_ROOT) { $env:MERIDIAN_ROOT = (Resolve-Path "$PSScriptRoot\..").Path }
Set-Location $env:MERIDIAN_ROOT
python src/automation/retrain.py --promote
if ($LASTEXITCODE -ne 0) { Write-Host "retrain exited $LASTEXITCODE" }
python src/automation/gates.py
