# Start official OpenAlgo (https://github.com/marketcalls/openalgo)
# Clone lives next to MeridianV4: ..\openalgo
$ErrorActionPreference = "Stop"
$oa = Join-Path (Resolve-Path "$PSScriptRoot\..\..") "openalgo"
if (-not (Test-Path "$oa\app.py")) { throw "OpenAlgo not found at $oa. git clone https://github.com/marketcalls/openalgo.git `"$oa`"" }
Set-Location $oa
if (-not (Test-Path ".env")) { Copy-Item ".sample.env" ".env" }
uv run app.py
