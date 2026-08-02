# /// script
# requires-python = ">=3.11"
# dependencies = ["acryl-datahub>=1.6,<2"]
# ///

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass, field

from datahub.emitter.mce_builder import (
    make_dashboard_urn,
    make_data_platform_urn,
    make_dataset_urn,
    make_group_urn,
    make_schema_field_urn,
    make_tag_urn,
)
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DataHubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    ChangeAuditStampsClass,
    CorpGroupInfoClass,
    DashboardInfoClass,
    DatasetLineageTypeClass,
    DatasetPropertiesClass,
    FineGrainedLineageClass,
    FineGrainedLineageDownstreamTypeClass,
    FineGrainedLineageUpstreamTypeClass,
    GlobalTagsClass,
    NumberTypeClass,
    OtherSchemaClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    TagAssociationClass,
    TagPropertiesClass,
    UpstreamClass,
    UpstreamLineageClass,
)


ACTOR_URN = "urn:li:corpuser:datahub"


@dataclass(frozen=True)
class Field:
    name: str
    native_type: str
    description: str
    is_key: bool = False


@dataclass(frozen=True)
class Dataset:
    platform: str
    name: str
    description: str
    fields: tuple[Field, ...]
    owners: tuple[str, ...]
    tags: tuple[str, ...]
    quality_signals: tuple[str, ...] = ()
    upstreams: tuple[str, ...] = ()
    field_lineage: dict[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)

    @property
    def urn(self) -> str:
        return make_dataset_urn(self.platform, self.name, "PROD")


ROOT = Dataset(
    platform="snowflake",
    name="analytics.customer_360",
    description="Canonical customer profile used across finance, growth, and ML.",
    fields=(
        Field("customer_id", "VARCHAR", "Stable customer identifier.", is_key=True),
        Field("email_hash", "VARCHAR", "One-way hash used for privacy-safe matching."),
        Field("lifetime_value", "NUMBER(18,2)", "Recognized customer lifetime value."),
        Field("last_order_at", "TIMESTAMP_NTZ", "Most recent completed order timestamp."),
        Field("churn_score", "FLOAT", "Current production churn propensity score."),
    ),
    owners=("Customer Data Platform",),
    tags=("Tier 1", "PII", "Certified"),
    quality_signals=("customer_id uniqueness assertion", "daily freshness SLA"),
)

FINANCE = Dataset(
    platform="dbt",
    name="finance.monthly_revenue",
    description="Monthly recognized revenue by customer segment.",
    fields=(
        Field("month", "DATE", "Accounting month."),
        Field("customer_id", "VARCHAR", "Customer identifier.", is_key=True),
        Field("recognized_revenue", "NUMBER(18,2)", "Revenue recognized in the month."),
    ),
    owners=("Finance Analytics",),
    tags=("Tier 1", "SOX"),
    quality_signals=("revenue reconciliation check",),
    upstreams=(ROOT.urn,),
    field_lineage={
        ROOT.urn: (
            ("customer_id", "customer_id"),
            ("lifetime_value", "recognized_revenue"),
        )
    },
)

ML = Dataset(
    platform="dbt",
    name="ml.churn_features",
    description="Feature view for the production churn model.",
    fields=(
        Field("customer_id", "VARCHAR", "Customer identifier.", is_key=True),
        Field("lifetime_value_90d", "NUMBER(18,2)", "Trailing 90-day customer value."),
        Field("days_since_order", "INTEGER", "Days since the last completed order."),
    ),
    owners=("Lifecycle ML",),
    tags=("Production ML",),
    quality_signals=("feature null-rate monitor",),
    upstreams=(ROOT.urn,),
    field_lineage={
        ROOT.urn: (
            ("customer_id", "customer_id"),
            ("lifetime_value", "lifetime_value_90d"),
            ("last_order_at", "days_since_order"),
        )
    },
)

GROWTH = Dataset(
    platform="snowflake",
    name="growth.campaign_segments",
    description="Daily activation audiences for lifecycle campaigns.",
    fields=(
        Field("customer_id", "VARCHAR", "Customer identifier.", is_key=True),
        Field("segment", "VARCHAR", "Current lifecycle segment."),
        Field("eligible_at", "TIMESTAMP_NTZ", "Audience eligibility timestamp."),
    ),
    owners=("Growth Engineering",),
    tags=("Daily Activation",),
    quality_signals=("segment volume anomaly",),
    upstreams=(ROOT.urn,),
    field_lineage={
        ROOT.urn: (
            ("customer_id", "customer_id"),
            ("churn_score", "segment"),
        )
    },
)

DATASETS = (ROOT, FINANCE, ML, GROWTH)

TAG_COLORS = {
    "Tier 1": "#C0392B",
    "PII": "#A93226",
    "Certified": "#1E8449",
    "SOX": "#7D3C98",
    "Production ML": "#2471A3",
    "Daily Activation": "#B9770E",
    "ImpactLint Reviewed": "#146C94",
}


def normalized_tag_urn(tag: str) -> str:
    return make_tag_urn(tag.replace(" ", ""))


def emit_aspect(emitter: DataHubRestEmitter, urn: str, aspect: object) -> None:
    emitter.emit_mcp(MetadataChangeProposalWrapper(entityUrn=urn, aspect=aspect))


def schema_type(native_type: str) -> SchemaFieldDataTypeClass:
    numeric = any(token in native_type for token in ("NUMBER", "FLOAT", "INTEGER"))
    return SchemaFieldDataTypeClass(type=NumberTypeClass() if numeric else StringTypeClass())


def seed_dataset(emitter: DataHubRestEmitter, dataset: Dataset) -> None:
    custom_properties = {
        "impactlint.quality_signals": "|".join(dataset.quality_signals),
        "impactlint.depends_on_fields": ",".join(
            sorted({source for mappings in dataset.field_lineage.values() for source, _ in mappings})
        ),
    }
    emit_aspect(
        emitter,
        dataset.urn,
        DatasetPropertiesClass(
            name=dataset.name,
            qualifiedName=dataset.name,
            description=dataset.description,
            customProperties=custom_properties,
        ),
    )
    emit_aspect(
        emitter,
        dataset.urn,
        SchemaMetadataClass(
            schemaName=dataset.name,
            platform=make_data_platform_urn(dataset.platform),
            version=0,
            hash="",
            platformSchema=OtherSchemaClass(rawSchema=""),
            fields=[
                SchemaFieldClass(
                    fieldPath=item.name,
                    type=schema_type(item.native_type),
                    nativeDataType=item.native_type,
                    nullable=not item.is_key,
                    description=item.description,
                    isPartOfKey=item.is_key,
                )
                for item in dataset.fields
            ],
            primaryKeys=[item.name for item in dataset.fields if item.is_key],
        ),
    )
    emit_aspect(
        emitter,
        dataset.urn,
        OwnershipClass(
            owners=[
                OwnerClass(owner=make_group_urn(owner), type=OwnershipTypeClass.TECHNICAL_OWNER)
                for owner in dataset.owners
            ]
        ),
    )
    emit_aspect(
        emitter,
        dataset.urn,
        GlobalTagsClass(tags=[TagAssociationClass(tag=normalized_tag_urn(tag)) for tag in dataset.tags]),
    )

    if dataset.upstreams:
        fine_grained = []
        for upstream_urn, mappings in dataset.field_lineage.items():
            for source_field, target_field in mappings:
                fine_grained.append(
                    FineGrainedLineageClass(
                        upstreamType=FineGrainedLineageUpstreamTypeClass.FIELD_SET,
                        downstreamType=FineGrainedLineageDownstreamTypeClass.FIELD,
                        upstreams=[make_schema_field_urn(upstream_urn, source_field)],
                        downstreams=[make_schema_field_urn(dataset.urn, target_field)],
                        confidenceScore=1.0,
                    )
                )
        emit_aspect(
            emitter,
            dataset.urn,
            UpstreamLineageClass(
                upstreams=[
                    UpstreamClass(dataset=urn, type=DatasetLineageTypeClass.TRANSFORMED)
                    for urn in dataset.upstreams
                ],
                fineGrainedLineages=fine_grained,
            ),
        )


def seed_dashboard(emitter: DataHubRestEmitter) -> str:
    urn = make_dashboard_urn("looker", "executive.revenue_overview")
    stamp = AuditStampClass(time=int(time.time() * 1000), actor=ACTOR_URN)
    emit_aspect(
        emitter,
        urn,
        DashboardInfoClass(
            title="executive.revenue_overview",
            description="Executive revenue and customer value dashboard.",
            lastModified=ChangeAuditStampsClass(created=stamp, lastModified=stamp),
            datasets=[FINANCE.urn],
            customProperties={"impactlint.depends_on_fields": "customer_id,lifetime_value"},
        ),
    )
    emit_aspect(
        emitter,
        urn,
        OwnershipClass(
            owners=[
                OwnerClass(
                    owner=make_group_urn("Business Intelligence"),
                    type=OwnershipTypeClass.TECHNICAL_OWNER,
                )
            ]
        ),
    )
    emit_aspect(
        emitter,
        urn,
        GlobalTagsClass(
            tags=[TagAssociationClass(tag=normalized_tag_urn(tag)) for tag in ("Executive", "Tier 1")]
        ),
    )
    return urn


def seed(gms_url: str, token: str | None) -> None:
    emitter = DataHubRestEmitter(gms_server=gms_url, token=token)
    emitter.test_connection()

    owners = sorted({owner for dataset in DATASETS for owner in dataset.owners} | {"Business Intelligence"})
    for owner in owners:
        emit_aspect(
            emitter,
            make_group_urn(owner),
            CorpGroupInfoClass(
                displayName=owner,
                description=f"Owner group for {owner} data products.",
                admins=[],
                members=[],
                groups=[],
            ),
        )

    for tag, color in {**TAG_COLORS, "Executive": "#6C3483"}.items():
        emit_aspect(
            emitter,
            normalized_tag_urn(tag),
            TagPropertiesClass(name=tag, description=f"ImpactLint demo tag: {tag}.", colorHex=color),
        )

    for dataset in DATASETS:
        seed_dataset(emitter, dataset)
    dashboard_urn = seed_dashboard(emitter)
    emitter.close()

    print(f"Seeded {len(DATASETS)} datasets and 1 dashboard into {gms_url}")
    print(f"Root dataset: {ROOT.urn}")
    print(f"Dashboard: {dashboard_urn}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ImpactLint DataHub demo catalog")
    parser.add_argument("--gms-url", default=os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.getenv("DATAHUB_GMS_TOKEN") or None)
    args = parser.parse_args()
    seed(args.gms_url, args.token)


if __name__ == "__main__":
    main()
