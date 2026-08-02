from impactlint.models import Asset, CatalogContext, GraphEdge, Scenario

ROOT_URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.customer_360,PROD)"


SCENARIOS = [
    Scenario(
        id="customer-key-rename",
        name="Rename a shared customer key",
        description="A breaking warehouse change with dashboard, finance, and ML consumers.",
        dataset_urn=ROOT_URN,
        dialect="snowflake",
        change_sql=("ALTER TABLE analytics.customer_360\nRENAME COLUMN customer_id TO customer_key;"),
    ),
    Scenario(
        id="drop-lifetime-value",
        name="Drop a derived revenue field",
        description="A field removal that reaches executive reporting and churn features.",
        dataset_urn=ROOT_URN,
        dialect="snowflake",
        change_sql="ALTER TABLE analytics.customer_360 DROP COLUMN lifetime_value;",
    ),
]


def fixture_context() -> CatalogContext:
    assets = [
        Asset(
            urn=ROOT_URN,
            name="analytics.customer_360",
            platform="Snowflake",
            layer=0,
            description="Canonical customer profile used across finance, growth, and ML.",
            fields=[
                "customer_id",
                "email_hash",
                "lifetime_value",
                "last_order_at",
                "churn_score",
            ],
            owners=["Customer Data Platform"],
            tags=["Tier 1", "PII", "Certified"],
            quality_signals=["customer_id uniqueness assertion", "daily freshness SLA"],
        ),
        Asset(
            urn="urn:li:dataset:(urn:li:dataPlatform:dbt,finance.monthly_revenue,PROD)",
            name="finance.monthly_revenue",
            platform="dbt",
            layer=1,
            description="Monthly recognized revenue by customer segment.",
            fields=["month", "customer_id", "recognized_revenue"],
            depends_on_fields=["customer_id", "lifetime_value"],
            owners=["Finance Analytics"],
            tags=["Tier 1", "SOX"],
            quality_signals=["revenue reconciliation check"],
        ),
        Asset(
            urn="urn:li:dataset:(urn:li:dataPlatform:dbt,ml.churn_features,PROD)",
            name="ml.churn_features",
            platform="dbt",
            layer=1,
            description="Feature view for the production churn model.",
            fields=["customer_id", "lifetime_value_90d", "days_since_order"],
            depends_on_fields=["customer_id", "lifetime_value", "last_order_at"],
            owners=["Lifecycle ML"],
            tags=["Production ML"],
            quality_signals=["feature null-rate monitor"],
        ),
        Asset(
            urn="urn:li:dataset:(urn:li:dataPlatform:looker,executive.revenue_overview,PROD)",
            name="executive.revenue_overview",
            platform="Looker",
            kind="dashboard",
            layer=2,
            description="Executive revenue and customer value dashboard.",
            depends_on_fields=["customer_id", "lifetime_value"],
            owners=["Business Intelligence"],
            tags=["Executive", "Tier 1"],
        ),
        Asset(
            urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,growth.campaign_segments,PROD)",
            name="growth.campaign_segments",
            platform="Snowflake",
            layer=1,
            description="Daily activation audiences for lifecycle campaigns.",
            fields=["customer_id", "segment", "eligible_at"],
            depends_on_fields=["customer_id", "churn_score"],
            owners=["Growth Engineering"],
            tags=["Daily Activation"],
            quality_signals=["segment volume anomaly"],
        ),
    ]
    edges = [
        GraphEdge(source=ROOT_URN, target=assets[1].urn),
        GraphEdge(source=ROOT_URN, target=assets[2].urn),
        GraphEdge(source=assets[1].urn, target=assets[3].urn),
        GraphEdge(source=ROOT_URN, target=assets[4].urn),
    ]
    return CatalogContext(root_urn=ROOT_URN, assets=assets, edges=edges, source="fixture")
