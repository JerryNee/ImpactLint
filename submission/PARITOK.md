# Paritok submission copy

## Project name

ImpactLint

## Tagline

Evidence-safe warehouse change reviews with 67.6% less reasoning context.

## Project URL

https://impactlint.vercel.app

## Repository

https://github.com/JerryNee/ImpactLint

## Demo video

https://youtu.be/I5Kou4vthdM

## Built with

Paritok, DataHub MCP, FastAPI, React, TypeScript, sqlglot, XYFlow, Vercel

## Submission story

### Inspiration

A warehouse migration can look like a one-line SQL edit while silently breaking finance models, executive dashboards, quality assertions, and ML features. The metadata needed to review that change exists in a catalog, but sending a full catalog response to every reasoning step is slow and expensive. ImpactLint makes that review both context-aware and token-efficient.

### What it does

ImpactLint accepts a proposed schema change, parses the SQL into structured operations, reads downstream lineage and governance metadata, and produces a deterministic risk score backed by inspectable evidence. It identifies affected assets and owners, visualizes the impact graph, and generates a migration plan, dbt tests, and a machine-readable review manifest. In live DataHub mode it can publish the completed analysis back as a DataHub document and tag the source asset.

### How Paritok is used

The raw DataHub entity and lineage responses are normalized into line-oriented evidence, divided into bounded segments, and sent concurrently to Paritok's hosted GPU through `/api/compress`. The returned context is then checked by an extractive evidence guard: only complete source lines are accepted, invented rewrites are discarded, and required change, asset, lineage, and identifier evidence is restored before the final token count is reported.

On the checked-in live run, the DataHub review context contained 7,635 tokens. Paritok returned 2,476 tokens and the guarded final context contained 2,475 tokens, a measured 67.6% reduction. Eighteen required evidence lines and 25 protected identifiers were checked; one line and zero identifiers needed restoration. The public fixture demo intentionally has a much smaller input and reports its lower reduction honestly.

### What I am proud of

- Paritok is part of a genuine data-engineering workflow, not a decorative API call.
- Original, raw model-output, and guarded-final token counts remain separate.
- Compression failure never blocks a deterministic impact review or creates fake savings.
- Every result links back to concrete SQL, DataHub metadata, lineage, ownership, tags, and quality signals.
- Sample artifacts and a non-secret measured run are committed for independent inspection.

### Challenges and lessons

Compression quality cannot be judged by token reduction alone. During development, a compressed response rewrote a required evidence line and an earlier exploratory response introduced an unsupported tier. That led to the source-line and identifier guards now built into ImpactLint. The result is a practical pattern for using lossy context compression in audit-sensitive agent workflows.

### What is next

The next step is a CI integration that reviews migration pull requests automatically, publishes findings to DataHub, and reruns only the affected dbt contracts after owners approve the plan.

## Feedback entry

The hosted compression response currently exposes `compressed` and `gpu_available`, but not auditable usage or provenance. ImpactLint has to calculate token counts locally with an assumed tokenizer and cannot reconcile a review with dashboard accounting. A structured response containing input/output token counts, tokenizer, model version, request ID, and latency would make measured savings independently reproducible. Optional selected source spans would also let evidence-sensitive clients verify retention without heuristics.

Submitted as [Paritok issue #18](https://github.com/Paritok-official/paritok-4b-v1/issues/18).
