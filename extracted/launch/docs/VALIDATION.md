# Validation performed

- 30 tests passed with the installed, pinned Python dependencies.
- HTTP tests verify initial HTML content and JSON-LD on module/document pages.
- HTML/REST signal parity and MCP/REST parity are checked against clearly identified test fixtures.
- A real MCP initialize → tools/list → tools/call exchange passed, including API-key ownership shared with REST.
- Private scan access, free scan quotas, invalid API keys and incomplete-score badge gating are checked.
- SSRF tests cover local/private IPs, credentials, ports and mixed DNS answers.
- Ed25519 result verification and exclusion of community runs from ranked results are checked.
- UK compensation distance/delay boundaries, uncertain eligibility and intra-EU bands are tested.
- HTML/JSON sanitisation/error handling and actual PDF text extraction from a generated fixture are checked.
- Python compilation, JavaScript syntax and Compose YAML parsing passed.
- Renderer network configuration contains only internal networks; the GET broker is the egress path.
- Official x402 EVM middleware imports were verified. No real or testnet payment was made.

Not verified here: live external scans, first Environment Agency ingestion, Chromium execution, Docker image build/runtime, browser visual QA, production Redis/PostgreSQL concurrency, Stripe webhook lifecycle, x402 settlement/replay, delivery to an actual webhook, registry publication and deployed MCP client connections.

The environment could not resolve example.com or environment.data.gov.uk through the runtime network. Chromium download failed and Docker is unavailable. Tests do not substitute for these deployment checks. No browser-rendered score was fabricated to compensate.

Discovery update: 33 tests passed, including stored score HTML, history, private-report exclusion, canonical links, sitemap, explicit robots groups and reference pages. IndexNow live delivery and registry validation were not run.
