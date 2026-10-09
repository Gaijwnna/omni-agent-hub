# Omni-Agent Hub

**The growth engine for the agentic web.**

Scan any website for AI agent compatibility. Benchmark your agent on real browser tasks. Track improvement over time. Access everything via HTML, REST, or MCP — whichever your stack uses.

→ Live: [http://84.8.158.221](http://84.8.158.221)
→ API: [http://84.8.158.221/openapi.json](http://84.8.158.221/openapi.json)
→ MCP: [http://84.8.158.221/mcp](http://84.8.158.221/mcp)
→ Agent manifest: [http://84.8.158.221/.well-known/agent.json](http://84.8.158.221/.well-known/agent.json)

---

## What it does

### Readiness Scanner
Fetches a public URL and scores it across eight checks (100 points total):

| Check | Points | What it measures |
|---|---:|---|
| Semantic HTML | 20 | `<main>`, single `<h1>`, native controls, table headers |
| Input labels | 15 | Every control has an associated label |
| Layout stability | 12 | CLS ≤ 0.1 during 5 seconds at 1365×768 |
| CAPTCHA barriers | 10 | Known CAPTCHA markup patterns |
| llms.txt | 8 | Valid text document at `/llms.txt` |
| Crawler policy | 10 | Named-agent `robots.txt` permissions |
| Initial HTML | 15 | Raw text / rendered text ratio |
| API discovery | 10 | OpenAPI, agent.json, MCP endpoint, or ai-plugin.json |

A complete report (100% coverage) produces a 0–100 score and enables an embeddable badge. Each failing check includes the exact code to add.

### Open Agent Benchmark
Seven seeded browser challenges covering nested menus, matrix selection, multi-step forms, shifting state, iframes, date pickers, and file uploads. Results are signed with Ed25519. Community track is always open. Verified track requires an independent witnessing harness.

### MCP Server
All scanner and benchmark capabilities are available as MCP tools via `POST /mcp`. Connect any MCP-compatible agent client to scan sites, run benchmarks, retrieve public scores, and check flood signals directly from your agent session.

---

## Quickstart (Docker)

```sh
git clone https://github.com/Gaijwnna/omni-agent-hub.git
cd omni-agent-hub/server

cp .env.example .env
# Edit .env — at minimum set APP_SECRET and POSTGRES_PASSWORD
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock
python -m app.manage generate-secrets  # fills APP_SECRET and BENCHMARK_SIGNING_KEY

docker compose up --build -d
```

The app starts at `http://localhost:8000`. Put HTTPS in front of it before production (`ops/nginx.conf` is a ready starting point).

## Local development (no Docker)

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock
cp .env.example .env
python -m app.manage generate-secrets
uvicorn app.main:app --reload --port 8000
# separate shell:
python -m app.worker
```

SQLite and a process-local rate limiter are used automatically when PostgreSQL/Redis are not configured.

## Run tests

```sh
python -m pytest -q
python -m compileall -q app
node --check sdk/javascript/index.js
```

33 tests pass. See `docs/VALIDATION.md` for the full test report.

---

## Architecture

```
Browser / curl / AI client
         │
    ┌────┴────────────────────────────────┐
    │  FastAPI   HTML · REST · MCP        │
    └──────┬──────────────────────────────┘
           │
    ┌──────┴──────┐    ┌──────────────┐
    │  PostgreSQL  │    │  Redis quota │
    └──────┬──────┘    └──────────────┘
           │
    ┌──────┴──────┐    ┌──────────────┐
    │   Worker    │───▶│  Chromium    │
    └─────────────┘    │  renderer    │
                       └──────────────┘
```

All three interfaces — HTML, `/api/v1/`, and `/mcp` — call the same service functions. Reports are persisted once and rendered or serialized on demand. No client JavaScript is required to read a result.

Full architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `APP_SECRET` | Yes | 32+ char random secret |
| `POSTGRES_PASSWORD` | Docker | PostgreSQL password |
| `PUBLIC_URL` | Production | Full HTTPS URL of the service |
| `CONTROLLER_NAME` | Production | Legal entity name |
| `CONTACT_EMAIL` | Production | Operator contact address |
| `BENCHMARK_SIGNING_KEY` | Yes | Base64-encoded Ed25519 private key |
| `REDIS_URL` | Production | Redis connection URL |
| `RENDERER_URL` | Optional | Chromium renderer service URL |
| `STRIPE_SECRET_KEY` | Optional | Enable Stripe billing |
| `X402_ENABLED` | Optional | Set to `1` to enable x402 payments |
| `INDEXNOW_KEY` | Optional | IndexNow ownership key |
| `ENVIRONMENT` | Optional | Set to `production` to enforce all checks |

---

## SDK

### Python
```python
import httpx

# Scan a site
resp = httpx.post("http://84.8.158.221/api/v1/scans", json={"url": "https://example.com", "public": True})
scan = resp.json()
print(scan["report_url"])  # /scans/<id>

# Get result
result = httpx.get(f"http://84.8.158.221{scan['report_url']}").json()
print(result["report"]["score"])
```

### JavaScript / Node
```js
// See sdk/javascript/index.js for the full client
const { OmniAgentHub } = require('./sdk/javascript');
const hub = new OmniAgentHub({ baseUrl: 'http://84.8.158.221' });
const scan = await hub.createScan({ url: 'https://example.com', public: true });
```

### MCP (Claude, cursor, etc.)
Add to your MCP config:
```json
{
  "mcpServers": {
    "omni-agent-hub": {
      "url": "http://84.8.158.221/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## What's next

See [docs/LAUNCH_STATUS.md](docs/LAUNCH_STATUS.md) for the full gap list. Key remaining items:
- Production HTTPS + domain
- Stripe / x402 payment integration
- Trusted browser execution harness for verified benchmark track
- Retailer availability adapter
- Certification workflow

---

## Licence

Service implementation: proprietary — see `LICENSE`.  
SDKs (`sdk/`): limited client-integration licence — see `sdk/*/LICENSE`.  
Environment Agency data: Open Government Licence v3.0.
