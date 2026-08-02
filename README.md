# ImpactLint

ImpactLint reviews proposed warehouse schema changes against catalog metadata before they reach production. It parses SQL, traces downstream lineage, scores risk from ownership, tags, and quality signals, then produces a migration plan and CI-friendly review artifacts.

The application is being built for the 2026 DataHub Agent Hackathon and Paritok Token Efficiency Hackathon. It supports a self-contained demo catalog and optional live integrations with DataHub MCP and the Paritok proxy.

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

Copy `.env.example` to `.env` and add credentials only when using live integrations. Fixture mode requires no account or API key.

## Verification

```bash
npm test
npm run lint
npm run build
```

## License

Apache License 2.0. See `LICENSE`.
