from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from impactlint.catalog import CatalogProvider
from impactlint.change_parser import parse_change
from impactlint.engine import affected_assets, context_payload, generate_artifacts, score_review
from impactlint.models import (
    Integration,
    IntegrationStatus,
    ReviewRequest,
    ReviewResponse,
    RunStep,
)
from impactlint.paritok import ParitokClient


class ReviewService:
    def __init__(self, catalog: CatalogProvider, paritok: ParitokClient, mode: str) -> None:
        self.catalog = catalog
        self.paritok = paritok
        self.mode = mode
        self.reviews: dict[str, ReviewResponse] = {}

    async def create_review(self, request: ReviewRequest) -> ReviewResponse:
        steps: list[RunStep] = []

        started = perf_counter()
        operations = parse_change(request.change_sql, request.dialect)
        steps.append(_step("parse", "Parse proposed SQL", "Structured with sqlglot", started))

        started = perf_counter()
        context = await self.catalog.get_context(request.dataset_urn)
        target = next(asset for asset in context.assets if asset.urn == context.root_urn)
        steps.append(
            _step(
                "context",
                "Gather catalog context",
                f"{len(context.assets)} assets and {len(context.edges)} lineage edges",
                started,
            )
        )

        started = perf_counter()
        affected = affected_assets(context, operations)
        score, level, signals = score_review(context, operations, affected)
        steps.append(
            _step(
                "impact",
                "Trace downstream impact",
                f"{len(affected)} affected assets; {len(signals)} evidence groups",
                started,
            )
        )

        started = perf_counter()
        artifacts = generate_artifacts(target, operations, affected, score)
        steps.append(_step("artifacts", "Generate migration artifacts", f"{len(artifacts)} files", started))

        started = perf_counter()
        payload = context_payload(context, operations, affected)
        explanation, compression = await self.paritok.explain(
            payload,
            "Explain the highest-risk evidence and the safest migration sequence in four sentences.",
        )
        steps.append(
            _step(
                "compression",
                "Optimize reasoning context",
                "Measured by Paritok" if compression.status == "measured" else "Paritok not connected",
                started,
                status="complete" if compression.status == "measured" else "skipped",
            )
        )

        field = operations[0].field or "the changed field"
        owner_count = len({owner for asset in [target, *affected] for owner in asset.owners})
        default_summary = (
            f"Changing {field} reaches {len(affected)} downstream assets across "
            f"{owner_count} owner groups. "
            "Use a compatibility window, update consumers and quality contracts, then remove the old field."
        )
        review_id = str(uuid4())
        review = ReviewResponse(
            id=review_id,
            created_at=datetime.now(UTC).isoformat(),
            risk_score=score,
            risk_level=level,
            headline=f"{level.value.title()} risk: coordinate before merge",
            summary=explanation or default_summary,
            operations=operations,
            target=target,
            affected_assets=affected,
            graph_assets=context.assets,
            graph_edges=context.edges,
            signals=signals,
            artifacts=artifacts,
            compression=compression,
            run_steps=steps,
            integrations=self.integrations(context.source),
        )
        self.reviews[review_id] = review
        return review

    def integrations(self, context_source: str | None = None) -> list[Integration]:
        datahub_live = self.mode == "datahub" or context_source == "datahub_mcp"
        return [
            Integration(
                id="datahub",
                label="DataHub MCP",
                status=IntegrationStatus.CONNECTED if datahub_live else IntegrationStatus.DEMO,
                detail="Live context graph" if datahub_live else "Seeded demo catalog",
            ),
            Integration(
                id="paritok",
                label="Paritok",
                status=IntegrationStatus.CONNECTED
                if self.paritok.configured
                else IntegrationStatus.UNAVAILABLE,
                detail="Compression measured" if self.paritok.configured else "Add API keys to measure",
            ),
        ]

    def get_review(self, review_id: str) -> ReviewResponse:
        try:
            return self.reviews[review_id]
        except KeyError as exc:
            raise LookupError(f"Review not found: {review_id}") from exc

    async def publish(self, review_id: str) -> tuple[ReviewResponse, str]:
        review = self.get_review(review_id)
        destination = await self.catalog.publish_review(review)
        updated = review.model_copy(update={"publish_status": "published"})
        self.reviews[review_id] = updated
        return updated, destination


def _step(
    step_id: str,
    label: str,
    detail: str,
    started: float,
    status: str = "complete",
) -> RunStep:
    duration_ms = max(1, round((perf_counter() - started) * 1000))
    return RunStep(id=step_id, label=label, status=status, detail=detail, duration_ms=duration_ms)
