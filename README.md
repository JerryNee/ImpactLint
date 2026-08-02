# ImpactLint

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-1f2d3d)](https://github.com/Paritok-official/paritok-4b-v1)
[![License](https://img.shields.io/badge/License-Apache%202.0-146c94)](LICENSE)

ImpactLint reviews proposed warehouse schema changes against catalog metadata before they reach production. It parses SQL, traces downstream lineage, scores risk from ownership, tags, and quality signals, then produces a migration plan and CI-friendly review artifacts.

The project is built for the 2026 DataHub Agent Hackathon and Paritok Token Efficiency Hackathon. It supports a self-contained fixture mode as well as live [DataHub MCP](https://github.com/acryldata/mcp-server-datahub) reads and writes. Built with [Paritok](https://github.com/Paritok-official/paritok-4b-v1) to compress the evidence packet on its hosted GPU before downstream reasoning.

## Workflow

1. Parse the proposed migration into a structured SQL AST with `sqlglot`.
2. Read schema, lineage, ownership, tags, and quality metadata through DataHub MCP.
3. Compute field-aware blast radius and a deterministic, evidence-backed risk score.
4. Send the complete evidence packet to Paritok's hosted GPU and measure the returned context.
5. Generate a migration plan, dbt guard, review manifest, and compressed-context sample.
6. Publish the review as a DataHub document and tag the source asset through MCP.

ImpactLint never invents token savings. The Paritok result is shown only after a successful hosted GPU response; otherwise the model step is marked as skipped.

## Local development

Requirements: Python 3.11+, `uv`, Node.js 20+, and npm.

```bash
uv sync
npm install
npm --prefix frontend install
npm run dev
```

Open `http://127.0.0.1:5173`. The API runs at `http://127.0.0.1:8000`.

## Configuration

Fixture mode requires no account or API key. Set values from `.env.example` in a local `.env` to enable live integrations.

```dotenv
IMPACTLINT_MODE=fixture
DATAHUB_MCP_URL=http://localhost:8001/mcp
DATAHUB_MCP_TOKEN=
PARITOK_API_URL=https://www.paritok.com/api
PARITOK_API_KEY=
PARITOK_MODEL=paritok-4b-v1
```

Secrets in `.env` are ignored by Git.

## Live DataHub demo

Start a local DataHub quickstart, seed the demo graph, and run the official MCP server:

```bash
datahub docker quickstart
uv run scripts/seed_datahub.py
git clone https://github.com/acryldata/mcp-server-datahub.git ../mcp-server-datahub
./scripts/start_datahub_mcp.sh
```

Set `IMPACTLINT_MODE=datahub`, then start ImpactLint with `npm run dev`. The seeded catalog contains four datasets, one Looker dashboard, field-level lineage, owners, tags, and quality signals. DataHub's local UI is available at `http://localhost:9002`.

`DATAHUB_MCP_REPO` can override the sibling MCP checkout used by the startup script.

## Hosted Paritok demo

Create a free API key in the [Paritok dashboard](https://www.paritok.com/dashboard), set `PARITOK_API_KEY`, and run a review. ImpactLint sends only the structured evidence packet to `POST /api/compress`; the response produces:

- Exact original and compressed token counts
- Tokens saved and reduction percentage
- `artifacts/paritok-context.txt`, containing the returned compressed context
- Usage associated with the API key in Paritok's official dashboard

## Verification

```bash
npm test
npm run lint
npm run build
```

The backend suite covers SQL parsing, impact scoring, official DataHub MCP payload normalization, exact multi-hop lineage, API behavior, and hosted Paritok success/failure handling. The frontend suite covers the primary review flow.

## License

Apache License 2.0. See `LICENSE`.
