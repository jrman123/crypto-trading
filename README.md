# AI Trading Stack (Vercel + Binance.US/.COM + Base44 + Zapier)

Production‑safe starter backend for an AI trading flow. Deployed on **Vercel** as Serverless Functions (Node 18, TypeScript). Connects to **Binance.US** or **Binance.com**, receives signals from **Base44**, and notifies **Zapier**.

## 🆕 Trading Knowledge System

This repository now includes a comprehensive **Trading Knowledge System** - a PostgreSQL-backed dataset and web-intelligence pipeline that powers crypto trading bots.

**Features:**
- 📊 Market data ingestion and storage
- 🔧 Technical feature engineering (RSI, MACD, EMA, SMA, Volatility)
- 📡 AI-powered trading signal generation
- 📝 Paper trading execution and portfolio tracking
- 🌐 Web intelligence with sentiment analysis
- 🛡️ Safety pause flags and system health monitoring
- 🔄 Complete pipeline automation

**[📖 Full Documentation](./TRADING_KNOWLEDGE_SYSTEM.md)** | **[🚀 Quick Demo](./examples/pipeline-demo.js)**

### Quick Example

```bash
# Run the complete pipeline: ingest → features → signal → trade
curl -X POST http://localhost:3000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "marketData": {
      "symbol": "BTCUSDT",
      "close": 50500,
      "volume": 1000
    },
    "autoTrade": true,
    "usdAmount": 100
  }'
```

See [TRADING_KNOWLEDGE_SYSTEM.md](./TRADING_KNOWLEDGE_SYSTEM.md) for complete setup and API documentation.

---

## Quickstart (Remote on Vercel)

1. **Install**: Node.js 18+ and Vercel CLI
   ```bash
   npm i -g vercel
   ```
2. **Create project folder** and deploy preview:
   ```bash
   vercel
   ```
3. **Set Env Vars** in Vercel (Project → Settings → Environment Variables) or via CLI:
   ```bash
   vercel env add BINANCE_API_KEY
   vercel env add BINANCE_API_SECRET
   vercel env add BINANCE_BASE_URL    # https://api.binance.us OR https://api.binance.com
   vercel env add BINANCE_TESTNET     # true|false  (ignored for .US)
   vercel env add ALLOWED_SYMBOLS     # e.g. BTCUSDT,ETHUSDT
   vercel env add MAX_QUOTE_PER_TRADE_USD  # e.g. 20
   vercel env add ZAPIER_WEBHOOK_URL  # optional
   ```
4. **Production deploy**:
   ```bash
   vercel --prod
   ```
5. **Test health**: open
   ```
   https://<PROJECT>.vercel.app/api/ping
   ```
6. **Test order (tiny)**:
   ```bash
   curl -X POST https://<PROJECT>.vercel.app/api/order      -H "Content-Type: application/json"      -d '{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","quoteOrderQty":"5","clientId":"test-1"}'
   ```

## Base44 Wiring

Add an **HTTP Request** / **Webhook** block:

- **URL**: `https://<PROJECT>.vercel.app/api/order`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "symbol": "{{pair}}",
  "side": "{{side}}",
  "type": "MARKET",
  "quoteOrderQty": "{{usd_to_spend}}",
  "clientId": "{{run_id}}"
}
```

Alternative endpoint (maps Base44 fields automatically): `https://<PROJECT>.vercel.app/api/webhook/base44`

## On‑Prem (Docker)

- Write a `.env` with the same variables.
- Provide your own reverse proxy (Caddy/Nginx) and HTTPS certs.
- Run the app with `node` (use `ts-node` or transpile with `tsc`). For a full on‑prem Docker compose you can adapt this repo easily.

## Safety Defaults

- Enforces `ALLOWED_SYMBOLS` and `MAX_QUOTE_PER_TRADE_USD`.
- `BINANCE_TESTNET=true` by default in `.env.example` (ignored for Binance.US).
- Never expose secrets in Base44 or Zapier.

---

© 2025-08-24
