# Omni-Agent Hub — private server source

This private repository contains the complete server release candidate in `Omni-Agent-Hub-Server-Release-Candidate.zip`. Extract it into a private checkout to work with the module tree. Backend code is proprietary; see the included LICENSE. Third-party dependencies retain their own licences.

The GitHub connector did not have access to this newly created repository, so the archive was committed through GitHub’s browser upload. Individual source files and GitHub Actions have not yet been imported into the repository tree.

## Included

- Architecture, container stack, PostgreSQL schema, REST routes and MCP definitions.
- Readiness scanner first, with safe network fetcher, browser worker and SSR reports.
- Materialized public score pages, history, sitemap, robots rules and IndexNow outbox.
- Benchmark community evaluator, official public-data adapter, flight claim drafts and PDF formatter.
- Disabled-until-configured Stripe/x402 adapters, SDK source, legal drafts and registry submission kit.
- 33 passing local tests. See launch/docs/VALIDATION.md and launch/docs/LAUNCH_STATUS.md.

## Deployment status

The existing public prototype is unchanged. This is not yet a revenue-ready launch. It requires a container host, domain, operator details and securely configured payment accounts, plus the remaining engineering and live verification listed in LAUNCH_STATUS.md. No fabricated scores, rankings or payment successes are included.

## Start

Extract the archive, open `launch/README.md`, and follow its container setup. Keep secrets out of git. A private repository and copyright notice protect access and copying of covered expression; they cannot prohibit independently developing similar functionality.

Archive SHA-256: `06dbe1005a8dfab583dfcf80ed23ef711975393e46a957b6de247fa8d8885259`
