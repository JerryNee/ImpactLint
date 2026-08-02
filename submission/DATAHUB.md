# DataHub submission copy

## Project name

ImpactLint

## Tagline

An evidence-backed agent that stops breaking warehouse changes before merge.

## Challenge

Primary: Agents That Do Real Work

Secondary: Metadata-Aware Code Generation & Development

## Project URL

https://impactlint.vercel.app

## Repository

https://github.com/JerryNee/ImpactLint

## Built with

DataHub MCP, Paritok, FastAPI, React, TypeScript, sqlglot, XYFlow, Vercel

## Submission story

### Inspiration

The dangerous part of a warehouse schema change is rarely the SQL itself. It is the invisible graph of dashboards, transformations, ML features, owners, governance tags, and quality contracts behind that SQL. Most pull-request checks cannot see that graph, so teams discover the real blast radius after deployment.

### What it does

ImpactLint is a metadata-aware change-review agent. A developer submits a proposed warehouse migration. ImpactLint parses the SQL, reads DataHub context through the official MCP server, traces field-aware downstream impact, and produces a deterministic risk decision with inspectable evidence. It generates a coordinated migration plan, dbt tests, and a JSON review manifest that can live in a pull request.

The workflow also writes knowledge back. Publishing a live review calls DataHub MCP `save_document` with the analysis and related assets, then `add_tags` to mark the source dataset as reviewed. The next engineer or agent inherits the decision instead of repeating the investigation.

### Meaningful use of DataHub

- `get_lineage` traces up to three downstream hops from the changed dataset.
- `get_entities` retrieves schemas, ownership, tags, descriptions, and quality metadata for every asset in scope.
- Additional upstream lineage calls reconstruct exact direct edges for deeper graph nodes.
- The risk engine cites DataHub evidence rather than asking an LLM to invent a score.
- `save_document` and `add_tags` publish the completed review back into the metadata graph.

The live quickstart scenario includes four datasets, a Looker dashboard, multi-hop lineage, five owner groups, governance tags, and quality signals. Renaming `customer_id` correctly produces a critical 100/100 decision, identifies four affected assets, and generates an executable compatibility plan.

### Technical execution

The backend is FastAPI and Python 3.12. `sqlglot` parses migrations into structured operations. A typed DataHub provider normalizes official MCP payloads without coupling the risk engine to response formatting. React and XYFlow provide the review, lineage, execution trace, and integration views. Paritok compresses large raw DataHub responses before downstream reasoning, with an extractive guard that rejects unsupported evidence.

The repository contains 12 backend tests and one primary frontend-flow test, reproducible fixture mode, live DataHub seeding scripts, measured integration output, generated examples, and a public Vercel deployment.

### What is next

ImpactLint can become a GitHub check that comments on migration pull requests, requests acknowledgements from DataHub owners, and blocks merge only when governed downstream assets lack a compatibility plan.

## Feedback survey notes

The MCP server made the read-context/write-result loop unusually direct. The most useful improvement would be a stable, documented normalized response schema for `get_entities` and `get_lineage`, including explicit direct-edge fields and field-level dependency references. That would reduce defensive recursive normalization in clients. A small official seeded quickstart graph covering ownership, tags, quality assertions, dashboards, and multi-hop lineage would also make end-to-end agent testing substantially faster.
