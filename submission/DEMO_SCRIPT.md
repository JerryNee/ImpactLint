# ImpactLint demo script

Target length: about 100 seconds.

## Narration

Warehouse schema changes rarely fail where they are authored. A one-line rename can break finance models, executive dashboards, quality checks, and machine-learning features several hops downstream.

ImpactLint reviews that change before merge. Here, a developer proposes renaming `customer_id` to `customer_key`. The SQL is parsed into a structured operation, then DataHub metadata supplies schema, lineage, ownership, governance tags, and quality signals.

The result is a critical risk score backed by inspectable evidence: four downstream assets, five owner groups, and five evidence categories. Nothing in this decision depends on an untraceable language-model score.

The lineage view makes the blast radius concrete, from the Snowflake customer table through dbt transformations to an executive Looker dashboard. The run log exposes each completed step and its latency.

Large DataHub responses are expensive to pass through an agent. ImpactLint sends bounded evidence segments to Paritok's hosted GPU, then applies an extractive guard that discards rewrites and restores required source lines and identifiers. In a measured live run, context fell from 7,635 tokens to 2,475, a 67.6 percent reduction, while all 25 protected identifiers survived.

Finally, ImpactLint generates a migration plan, dbt tests, and a machine-readable review manifest. In live mode, it publishes the analysis back to DataHub and tags the source asset, so the next engineer or agent inherits the decision.

ImpactLint turns a risky SQL diff into a review your data team can actually act on.
