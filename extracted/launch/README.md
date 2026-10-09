# Omni-Agent Hub — server release candidate

This is the container implementation, not a claim that the existing static website has been upgraded or that the service is ready to accept money. The original static prototype is preserved in `../dist`. Do not expose source files from `launch/` as web assets.

Start with [ARCHITECTURE.md](docs/ARCHITECTURE.md), then read [LAUNCH_STATUS.md](docs/LAUNCH_STATUS.md). The Readiness Scanner is implemented first in `app/network.py`, `app/scanner.py`, `app/renderer.py`, and `app/worker.py`.

## Local development

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
cp .env.example .env
# Set your own secrets locally; never commit .env.
python -m app.manage generate-secrets
uvicorn app.main:app --reload --port 8000
# In another shell with the same environment:
python -m app.worker
```

Local mode uses SQLite and a process-local rate limiter when PostgreSQL/Redis are not configured. It is for development only. `.env` is read automatically by Docker Compose; when running Python directly, load environment variables using your shell or `uvicorn --env-file .env`. The worker does not automatically source `.env`.

## Containers

1. Fill `.env`: application secret, database password, legal operator identity/contact and signing key. Keep payment keys empty initially.
2. Run `docker compose up --build -d`.
3. Put HTTPS in front of `127.0.0.1:8000`. Use `ops/nginx.conf` as a starting point.
4. Set the final `PUBLIC_URL`. Configure trusted-proxy IP handling explicitly; never trust arbitrary forwarded headers.
5. Use PostgreSQL backups, TLS, a secret manager, a hardened browser runtime and tested egress policy before opening to the public.
6. Set `ENVIRONMENT=production` only after completing the launch checks. That setting refuses missing controller/contact/HTTPS/Redis/secret configuration.

The renderer runs non-root with Chromium sandbox enabled. Some Docker hosts need a reviewed seccomp profile permitting user namespaces. Do not solve this by adding `--no-sandbox`. Docker and Chromium execution were unavailable in the authoring environment and must be validated on the target host.

## Verification

```sh
python -m pytest -q
python -m compileall -q app
node --check sdk/javascript/index.js
```

Tests use clearly identified fixtures in temporary databases, never seed production signals or rankings. Read the release's actual test result in `docs/VALIDATION.md`.

## Module order

1. Scanner and safe network fetcher.
2. Shared HTML/API/MCP services, rate limits and persistence.
3. Versioned benchmark, signed community results and gated leaderboard.
4. Environment Agency open-data adapter and event subscriptions.
5. UK261/EU261 direct-flight delay drafts.
6. Bounded server-side text/HTML/JSON/PDF conversion.
7. Stripe and x402 integration adapters, disabled until configured.
8. SDK packages, legal drafts, documentation and private-repository CI.

## Important limits

A complete numeric scanner score requires successful browser evidence. Missing checks remain unknown. A badge is an automated observation, not certification. The benchmark is currently a community challenge-answer evaluator; a signature does not establish agent identity or prove browser execution. Verified public rankings require an independently witnessed harness. Retailer inventory sources, paid certification fulfilment, monthly challenge releases, hosted private agent execution and registry publication are not represented as live services.

## Source protection

Keep this repository private. The service implementation has a proprietary rights notice. SDKs have a limited client-integration licence, not permission to copy the hosted backend. Public HTML, public schemas and visible challenge behaviour cannot be kept secret. Copyright does not confer ownership of an idea or independently developed functionality. See `docs/IP_AND_GITHUB.md`.
