# Launch status — candid release boundary

**This is a tested server implementation and architecture package, not a completed public commercial launch.** The existing Sites prototype remains unchanged. Container deployment and package publication have not occurred. A private GitHub repository was created; the release archive is being uploaded through the signed-in browser.

| Requirement | Current state | Remaining for public launch |
|---|---|---|
| Initial HTML, schemas, discovery | Implemented; HTTP tests | Production metadata/domain and visual/browser QA |
| Shared JSON/MCP module services | Implemented; transport tests | Client-specific connection checks; OAuth for paid ChatGPT access |
| Readiness scanner | Fetching, analysis, queue, reports, badge implemented | Live internet scan, browser/container smoke test, adversarial network review, operational limits |
| API-key quotas | Redis counters and local test fallback | Trusted proxy configuration, global/IP anti-key-farming limits, load tests |
| Open benchmark | Seeded seven-task answer evaluator and signed community results | Trusted browser execution harness; enforced multistep/dynamic-state tasks; environment evidence; repeated seeds; verified leaderboard promotion |
| Monthly challenge releases | Versioning design | Human-reviewed release process and scheduler; no schedule installed |
| Real data | EA adapter and attribution, no fabricated records | First successful network ingestion on the host |
| Claims | Direct-flight delay drafts and boundary tests | Current-law/operator review; wider cases intentionally unsupported |
| Formatter | Real server PDF/text pipeline and bounded subprocess | Host PDF extraction smoke/abuse tests, optional OCR, model-native tokenizers if desired |
| Availability | Approved-source change events, webhook retries, MCP polling | Retailer permission/source adapter; endpoint ownership verification; delivery audit/dead-letter operations |
| x402 | Official SDK adapter for premium scans, disabled | Wallet/facilitator; Base USDC testnet/mainnet settlement tests; request-bound idempotency; safe job/payment atomicity; paid MCP support |
| Stripe | Checkout and verified webhook adapter, disabled | Merchant account/products/prices, cancellation portal, lifecycle smoke tests and billing policy |
| Sponsored directory | Explicit flags/HTML labels | Sponsor contracts and fulfilment workflow |
| Certification | Schema, policy and unavailable product page | Domain proof, paid entitlement, reviewer flow, expiry/revocation and monthly jobs |
| Private/priority hosted benchmarks | Private community record entitlement only | Isolated agent execution, queue and actual paid fulfilment |
| npm/PyPI | Client source/package metadata | Verified namespace and registry credentials; publish and install tests |
| Legal/trust | Draft pages and controller configuration gate | Legal entity, contact, processors, hosting/transfer facts, billing retention, enforceable terms review |
| Source protection | Proprietary notice, private-source CI, deployment separation | Expanded Git source import/connector access, branch protection, secret scanning, human-authorship/ownership review |

No mock successes, made-up leaderboard entries, invented live values, false payment verification or fabricated certifications are used to bridge these gaps.

## Deploy in this order

1. Provision private repository, hosting domain and isolated container host.
2. Configure secrets, backups, DNS, TLS, allowed egress and real client-IP limits.
3. Run the scanner against owned fixture sites and a permitted live public target; verify raw/HTML/API/MCP parity and badge gating.
4. Launch the free scanner and official data adapter after privacy/operator details are complete.
5. Implement and validate the trusted benchmark harness before advertising ranked agent capability.
6. Enable Stripe and x402 only after real test-mode settlement, replay, cancellation and entitlement checks.
7. Add paid certification and retailer availability adapters after operational and terms reviews.

The package is intentionally explicit about the remaining engineering. A Dockerfile, a licence file and an HTTP 402 response alone do not make a launch trustworthy.

## Organic discovery added

Public completed scans are materialized as stored HTML at `/score/{domain}` with direct answers, canonical URLs, JSON-LD, public history and badge backlinks. The same snapshot is exposed as `/api/v1/scores/{domain}` and MCP `get_public_score`. The homepage defaults to publication with a visible opt-out; API/MCP callers retain explicit publication control and their existing private default. Previously private results are never published retroactively.

Crawler groups, sitemap shards, dataset/claim/API-reference pages and a durable IndexNow outbox are implemented. IndexNow remains disabled until a production URL and ownership key are configured. Receipt is not proof of indexing. Registry files are prepared, not submitted. Search placement, agent adoption and revenue are not guaranteed. Glama eligibility for proprietary hosted servers needs confirmation; never make the backend public just to obtain a listing.
