import json
from collections import defaultdict, deque

from impactlint.models import (
    Asset,
    CatalogContext,
    ChangeOperation,
    Evidence,
    GeneratedArtifact,
    ImpactSignal,
    Severity,
)

BREAKING_KINDS = {"rename_column", "drop_column", "alter_column"}
CRITICAL_TAGS = {"tier 1", "sox", "executive", "production ml", "pii"}


def affected_assets(context: CatalogContext, operations: list[ChangeOperation]) -> list[Asset]:
    asset_by_urn = {asset.urn: asset for asset in context.assets}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in context.edges:
        adjacency[edge.source].append(edge.target)

    changed_fields = {operation.field for operation in operations if operation.field}
    queue = deque([context.root_urn])
    visited = {context.root_urn}
    affected: list[Asset] = []
    while queue:
        current = queue.popleft()
        for child in adjacency[current]:
            if child in visited:
                continue
            visited.add(child)
            queue.append(child)
            asset = asset_by_urn.get(child)
            if asset is None:
                continue
            if not changed_fields or changed_fields.intersection(asset.depends_on_fields) or asset.layer > 1:
                affected.append(asset)
    return affected


def score_review(
    context: CatalogContext,
    operations: list[ChangeOperation],
    affected: list[Asset],
) -> tuple[int, Severity, list[ImpactSignal]]:
    target = next(asset for asset in context.assets if asset.urn == context.root_urn)
    breaking = any(operation.kind in BREAKING_KINDS for operation in operations)
    critical_assets = [
        asset
        for asset in [target, *affected]
        if CRITICAL_TAGS.intersection(tag.lower() for tag in asset.tags)
    ]
    owner_count = len({owner for asset in [target, *affected] for owner in asset.owners})
    quality_assets = [asset for asset in [target, *affected] if asset.quality_signals]

    score = 12
    score += 28 if breaking else 4
    score += min(28, len(affected) * 7)
    score += min(18, len(critical_assets) * 6)
    score += min(8, len(quality_assets) * 2)
    score += min(6, max(0, owner_count - 1) * 2)
    score = min(100, score)
    level = _risk_level(score)

    signals: list[ImpactSignal] = []
    if breaking:
        operation_names = ", ".join(operation.kind.replace("_", " ") for operation in operations)
        signals.append(
            ImpactSignal(
                id="breaking-change",
                severity=Severity.HIGH,
                title="Breaking schema operation",
                detail=f"The proposal contains {operation_names}; consumers require a coordinated migration.",
                evidence=[
                    Evidence(
                        source="SQL parser",
                        label="Parsed operation",
                        value=operation.rendered_sql,
                        asset_urn=target.urn,
                    )
                    for operation in operations
                ],
            )
        )
    if affected:
        signals.append(
            ImpactSignal(
                id="downstream-blast-radius",
                severity=Severity.HIGH if len(affected) >= 3 else Severity.MEDIUM,
                title=f"{len(affected)} downstream assets are in scope",
                detail="DataHub lineage connects the changed dataset to active transformations and products.",
                evidence=[
                    Evidence(
                        source="DataHub lineage",
                        label=asset.platform,
                        value=asset.name,
                        asset_urn=asset.urn,
                    )
                    for asset in affected
                ],
            )
        )
    if critical_assets:
        signals.append(
            ImpactSignal(
                id="governed-assets",
                severity=Severity.CRITICAL
                if any("sox" in (tag.lower() for tag in asset.tags) for asset in critical_assets)
                else Severity.HIGH,
                title="Governed and production-critical consumers",
                detail=(
                    "The impact includes assets carrying Tier 1, SOX, executive, PII, "
                    "or production ML metadata."
                ),
                evidence=[
                    Evidence(
                        source="DataHub tags",
                        label=asset.name,
                        value=", ".join(asset.tags),
                        asset_urn=asset.urn,
                    )
                    for asset in critical_assets
                ],
            )
        )
    if owner_count > 1:
        owners = sorted({owner for asset in [target, *affected] for owner in asset.owners})
        signals.append(
            ImpactSignal(
                id="cross-team-coordination",
                severity=Severity.MEDIUM,
                title=f"Coordinate with {owner_count} owner groups",
                detail="Ownership metadata shows that the migration crosses team boundaries.",
                evidence=[
                    Evidence(source="DataHub ownership", label="Owner", value=owner) for owner in owners
                ],
            )
        )
    if quality_assets:
        signals.append(
            ImpactSignal(
                id="quality-contracts",
                severity=Severity.MEDIUM,
                title="Existing quality contracts need updates",
                detail=(
                    "Assertions and monitors reference the affected data path and should move "
                    "with the change."
                ),
                evidence=[
                    Evidence(
                        source="DataHub quality",
                        label=asset.name,
                        value=", ".join(asset.quality_signals),
                        asset_urn=asset.urn,
                    )
                    for asset in quality_assets
                ],
            )
        )
    return score, level, signals


def generate_artifacts(
    target: Asset,
    operations: list[ChangeOperation],
    affected: list[Asset],
    score: int,
) -> list[GeneratedArtifact]:
    operation = operations[0]
    old_field = operation.field or "changed_field"
    new_field = operation.replacement or old_field
    if operation.kind == "rename_column":
        preparation_steps = (
            f"- [ ] Add `{new_field}` alongside `{old_field}` and backfill it.\n"
            "- [ ] Keep the old field available for one compatibility window."
        )
        cutover_step = f"- [ ] Remove `{old_field}` only after every owner acknowledges the change."
        test_path = "artifacts/schema.yml"
        test_language = "yaml"
        tests = f"""version: 2

models:
  - name: {target.name.split(".")[-1]}
    columns:
      - name: {new_field}
        data_tests:
          - not_null
          - unique
"""
        test_rationale = "Carries the key integrity contract onto the replacement field."
    elif operation.kind == "drop_column":
        preparation_steps = (
            f"- [ ] Mark `{old_field}` as deprecated in DataHub.\n"
            f"- [ ] Keep `{old_field}` available for one compatibility window while consumers migrate."
        )
        cutover_step = f"- [ ] Remove `{old_field}` only after every owner acknowledges the retirement."
        test_path = f"artifacts/assert_{old_field}_compatibility.sql"
        test_language = "sql"
        tests = f"""-- Keep this dbt test during the compatibility window.
select {old_field}
from {{{{ ref('{target.name.split(".")[-1]}') }}}}
where false
"""
        test_rationale = "Fails compilation if the field disappears before the compatibility window ends."
    else:
        preparation_steps = (
            f"- [ ] Deploy `{new_field}` as a backward-compatible change.\n"
            "- [ ] Validate nullability, type coercion, and historical backfill behavior."
        )
        cutover_step = "- [ ] Enforce the final contract only after downstream validation passes."
        test_path = "artifacts/schema.yml"
        test_language = "yaml"
        tests = f"""version: 2

models:
  - name: {target.name.split(".")[-1]}
    columns:
      - name: {new_field}
        data_tests:
          - not_null
"""
        test_rationale = "Adds a basic integrity check for the changed field."
    owner_lines = "\n".join(
        f"- [ ] Notify **{owner}**"
        for owner in sorted({owner for asset in affected for owner in asset.owners})
    )
    asset_lines = "\n".join(f"- [ ] Update `{asset.name}`" for asset in affected)
    migration = f"""# Migration plan for `{target.name}`

Risk score: **{score}/100**

## Before merge

{preparation_steps}
- [ ] Update DataHub descriptions, tags, and ownership notes.
{owner_lines}

## Consumer migration

{asset_lines}

## Cutover

- [ ] Confirm downstream freshness and quality assertions are green.
{cutover_step}
"""
    manifest = json.dumps(
        {
            "target": target.urn,
            "risk_score": score,
            "operations": [operation.model_dump() for operation in operations],
            "affected_assets": [asset.urn for asset in affected],
            "required_owners": sorted({owner for asset in affected for owner in asset.owners}),
        },
        indent=2,
    )
    return [
        GeneratedArtifact(
            kind="migration_plan",
            path="artifacts/migration-plan.md",
            language="markdown",
            content=migration,
            rationale="Sequences compatibility, consumer migration, and final removal.",
        ),
        GeneratedArtifact(
            kind="dbt_tests",
            path=test_path,
            language=test_language,
            content=tests,
            rationale=test_rationale,
        ),
        GeneratedArtifact(
            kind="review_manifest",
            path="artifacts/impactlint-review.json",
            language="json",
            content=manifest,
            rationale="Provides a machine-readable review artifact for CI and audit history.",
        ),
    ]


def context_payload(
    context: CatalogContext,
    operations: list[ChangeOperation],
    affected: list[Asset],
) -> dict:
    return {
        "target": next(asset.model_dump() for asset in context.assets if asset.urn == context.root_urn),
        "operations": [operation.model_dump() for operation in operations],
        "affected_assets": [asset.model_dump() for asset in affected],
        "lineage": [edge.model_dump() for edge in context.edges],
    }


def _risk_level(score: int) -> Severity:
    if score >= 85:
        return Severity.CRITICAL
    if score >= 65:
        return Severity.HIGH
    if score >= 40:
        return Severity.MEDIUM
    if score >= 20:
        return Severity.LOW
    return Severity.INFO
