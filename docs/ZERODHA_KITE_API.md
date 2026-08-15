# Zerodha Kite Connect — Personal (free) + static IP

Primary sources: [zerodha.com/products/api](https://zerodha.com/products/api/), [Kite API FAQs](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/kite-connect-api-faqs), [static IP](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip), [signup](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect), [Personal announcement](https://kite.trade/forum/discussion/14868/introducing-kite-connect-personal-apis-free-apis-for-personal-use), [OpenAlgo Zerodha](https://docs.openalgo.in/connect-brokers/brokers/zerodha).

## What is free

**Kite Connect Personal** is ₹0. You get:

- Orders, GTT, alerts
- Margins, positions, holdings, funds

You do **not** get:

- Live quotes / WebSocket ticks
- Historical candles
- `quote` / `ltp` (Zerodha: “Insufficient permission”)

Paid **Connect** = ₹500/month per API key (data + history). Zerodha has **no sandbox**.

For Meridian: Personal is enough to **place** paper/live orders through OpenAlgo. **Quote poll will fail** on Personal. Either pay Connect, or feed LTP from elsewhere (TradingView webhook, yfinance, etc.).

## Activate Personal API (you do this)

1. Open [developers.kite.trade/signup](https://developers.kite.trade/signup) (desktop mode if on phone).
2. Register with the **same email** as your Zerodha account.
3. Choose **Personal (Free)** — not Connect.
4. **My Apps → Create New App**
   - App name: e.g. `MeridianV4`
   - Zerodha **client ID** (your trading ID)
   - Redirect URL (must match OpenAlgo exactly):

```
http://127.0.0.1:5000/zerodha/callback
```

5. Save. Copy **API key** + **API secret**. Never commit them.
6. If login says `Invalid api_key`: pause the app, then set Active again.

Paste into `D:\work Dir\openalgo\.env` only:

```
BROKER_API_KEY = '<api key>'
BROKER_API_SECRET = '<api secret>'
REDIRECT_URL = 'http://127.0.0.1:5000/zerodha/callback'
```

Restart OpenAlgo → browser login → **Zerodha** → Kite PIN/TOTP → callback. Then OpenAlgo Analyzer ON for paper.

## Static IP (required for **orders**)

SEBI/NSE algo rules. Dedicated article: **effective 1 April 2026**. FAQs still say 1 April 2025. Either way, **unregistered IPs get order rejects now**.

| Still works from any IP | Needs whitelisted static IP |
|-------------------------|-----------------------------|
| Quotes (paid), WS, orderbook, positions | **Place / modify / cancel order** |

Static IP is **not** issued by Zerodha. Get one, then whitelist it.

### Get a static IP

Home Jio/Airtel Fiber is almost always **dynamic + CGNAT**. Whitelisting today’s `whatismyip` will break on reconnect.

Options (pick one):

1. **ISP static IPv4** — call Airtel/Jio/ACT, ask for a public static IPv4 on this connection. Often a small monthly add-on. Confirm it is **public** (not CGNAT).
2. **Tiny VPS in India (Mumbai)** — DigitalOcean / AWS Lightsail / Hetzner / any VPS. The VPS IPv4 is static. Run OpenAlgo **on that box** (or tunnel orders through it).
3. **Dedicated-IP VPN / proxy** — only if the **egress** IP is fixed and you send all Kite **order** traffic through it.

Check egress: `curl https://api.ipify.org` from the same machine that will call the API. That exact string must be whitelisted.

### Whitelist (Developer Console)

1. [developers.kite.trade/login](https://developers.kite.trade/login)
2. Top-right **Profile** → **IP Whitelist**
3. Enter primary static IP (IPv4 or IPv6). Optional second IP, one per line. Max **2**.
4. Confirm: *used exclusively by me and/or my immediate family*.
5. **Update**. **One change per calendar week.** Instant.

Account-level, not per-app. Same IPs cover all apps on that developer login. Family (spouse, dependent children/parents) may share; others = risk of key ban.

If orders still reject: egress is IPv6 but you only listed IPv4 (or vice versa). Match the protocol that actually leaves the box.

## OpenAlgo paper after this

1. Static IP whitelisted **and** OpenAlgo running from that IP.
2. Analyzer **ON**.
3. Login Zerodha inside OpenAlgo.
4. Meridian `MERIDIAN_MODE=paper` + OpenAlgo API key.

Personal plan: orders can work; `quotes`/`multiquotes` will not. Plan Connect (₹500) if you want Zerodha LTP for the loop.

Never put Kite keys in the Meridian repo.
