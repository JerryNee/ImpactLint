from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntegrationStatus(StrEnum):
    CONNECTED = "connected"
    DEMO = "demo"
    UNAVAILABLE = "unavailable"


class Asset(BaseModel):
    urn: str
    name: str
    platform: str
    kind: str = "dataset"
    layer: int = 0
    description: str = ""
    fields: list[str] = Field(default_factory=list)
    depends_on_fields: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    quality_signals: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str = "lineage"


class CatalogContext(BaseModel):
    root_urn: str
    assets: list[Asset]
    edges: list[GraphEdge]
    source: Literal["fixture", "datahub_mcp"]
    raw_evidence: dict[str, Any] = Field(default_factory=dict, exclude=True)


class Scenario(BaseModel):
    id: str
    name: str
    description: str
    dataset_urn: str
    change_sql: str
    dialect: str = "snowflake"


class ChangeOperation(BaseModel):
    kind: Literal["rename_column", "drop_column", "alter_column", "add_column", "unknown"]
    table: str | None = None
    field: str | None = None
    replacement: str | None = None
    rendered_sql: str


class ReviewRequest(BaseModel):
    dataset_urn: str
    change_sql: str
    dialect: str = "snowflake"

    @field_validator("dataset_urn", "change_sql")
    @classmethod
    def require_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class Evidence(BaseModel):
    source: str
    label: str
    value: str
    asset_urn: str | None = None


class ImpactSignal(BaseModel):
    id: str
    severity: Severity
    title: str
    detail: str
    evidence: list[Evidence]


class GeneratedArtifact(BaseModel):
    kind: Literal["migration_plan", "dbt_tests", "review_manifest", "compressed_context"]
    path: str
    language: str
    content: str
    rationale: str


class CompressionMetrics(BaseModel):
    status: Literal["measured", "not_connected"]
    original_tokens: int
    compressed_tokens: int | None = None
    model_output_tokens: int | None = None
    tokens_saved: int | None = None
    reduction_percent: float | None = None
    source_lines_selected: int = 0
    evidence_lines_checked: int = 0
    evidence_lines_restored: int = 0
    evidence_terms_checked: int = 0
    evidence_terms_restored: int = 0
    source: str


class RunStep(BaseModel):
    id: str
    label: str
    status: Literal["complete", "skipped", "failed"]
    detail: str
    duration_ms: int


class Integration(BaseModel):
    id: str
    label: str
    status: IntegrationStatus
    detail: str


class ReviewResponse(BaseModel):
    id: str
    created_at: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: Severity
    headline: str
    summary: str
    operations: list[ChangeOperation]
    target: Asset
    affected_assets: list[Asset]
    graph_assets: list[Asset]
    graph_edges: list[GraphEdge]
    signals: list[ImpactSignal]
    artifacts: list[GeneratedArtifact]
    compression: CompressionMetrics
    run_steps: list[RunStep]
    integrations: list[Integration]
    publish_status: Literal["not_published", "published"] = "not_published"


class PublishResponse(BaseModel):
    review_id: str
    status: Literal["published"]
    destination: str
