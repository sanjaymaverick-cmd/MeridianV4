# Paper test against official OpenAlgo

Server clone: `D:\work Dir\openalgo` ([marketcalls/openalgo](https://github.com/marketcalls/openalgo))  
URL: http://127.0.0.1:5000

## Start
```
.\scripts\start_openalgo.ps1
```

## First run (you, in the browser)
1. http://127.0.0.1:5000/setup — create admin (strong password).
2. Log in → **API Key** — copy it.
3. **Analyzer** → ON (₹1 Cr sandbox). Do not live-login a broker yet if you only want paper.
4. In a **new** PowerShell (never commit the key):

```
$env:OPENALGO_API_KEY = "<paste>"
$env:OPENALGO_HOST = "http://127.0.0.1:5000"
$env:MERIDIAN_ROOT = "D:\work Dir\MeridianV4"
$env:MERIDIAN_MODE = "paper"
$env:MERIDIAN_LOOP = "1"
$env:MERIDIAN_MAX_TICKS = "10"
$env:MERIDIAN_POLL_SEC = "15"
python src/openalgo/strategy_v4.py
```

Quotes need a broker session. Without one, Analyzer still accepts orders but LTP may error — connect Zerodha/Delta when you want real ticks.

`.env` stays inside `openalgo/`. Never copy keys into this repo.
