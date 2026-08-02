from typing import Any

from impactlint.catalog import DataHubMCPProvider

ROOT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.customer_360,PROD)"
FINANCE = "urn:li:dataset:(urn:li:dataPlatform:dbt,finance.monthly_revenue,PROD)"
DASHBOARD = "urn:li:dashboard:(looker,executive.revenue_overview)"


def _entity(
    urn: str,
    name: str,
    platform: str,
    owner: str,
    tags: list[tuple[str, str]],
    *,
    fields: list[str] | None = None,
    custom_properties: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "urn": urn,
        "name": name,
        "platform": {"urn": f"urn:li:dataPlatform:{platform}", "name": platform},
        "properties": {
            "name": name,
            "description": f"Description for {name}",
            "customProperties": custom_properties or [],
        },
        "ownership": {
            "owners": [
                {
                    "owner": {
                        "urn": f"urn:li:corpGroup:{owner}",
                        "name": owner,
                    }
                }
            ]
        },
        "tags": {
            "tags": [
                {
                    "tag": {
                        "urn": tag_urn,
                        "properties": {"name": display_name},
                    }
                }
                for tag_urn, display_name in tags
            ]
        },
    }
    if fields is not None:
        payload["schemaMetadata"] = {
            "fields": [{"fieldPath": field_name} for field_name in fields]
        }
    return payload


class StubDataHubProvider(DataHubMCPProvider):
    def __init__(self) -> None:
        super().__init__("http://datahub.test/mcp")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if name == "get_entities":
            return [
                _entity(
                    ROOT,
                    "analytics.customer_360",
                    "snowflake",
                    "Customer Data Platform",
                    [("urn:li:tag:Tier1", "Tier 1")],
                    fields=["customer_id", "lifetime_value"],
                    custom_properties=[
                        {
                            "key": "impactlint.quality_signals",
                            "value": "uniqueness assertion|daily freshness SLA",
                        }
                    ],
                ),
                _entity(
                    FINANCE,
                    "finance.monthly_revenue",
                    "dbt",
                    "Finance Analytics",
                    [("urn:li:tag:SOX", "SOX")],
                    fields=["customer_id", "recognized_revenue"],
                    custom_properties=[
                        {
                            "key": "impactlint.depends_on_fields",
                            "value": "customer_id,lifetime_value",
                        }
                    ],
                ),
                _entity(
                    DASHBOARD,
                    "executive.revenue_overview",
                    "looker",
                    "Business Intelligence",
                    [("urn:li:tag:Executive", "Executive")],
                ),
            ]
        if arguments["urn"] == ROOT:
            return {
                "downstreams": {
                    "searchResults": [
                        {"entity": {"urn": FINANCE, "type": "DATASET"}, "degree": 1},
                        {"entity": {"urn": DASHBOARD, "type": "DASHBOARD"}, "degree": 2},
                    ]
                }
            }
        return {
            "upstreams": {
                "searchResults": [
                    {"entity": {"urn": FINANCE, "type": "DATASET"}, "degree": 1}
                ]
            }
        }


async def test_datahub_context_normalizes_entities_and_exact_lineage() -> None:
    provider = StubDataHubProvider()

    context = await provider.get_context(ROOT)

    assert [asset.urn for asset in context.assets] == [ROOT, FINANCE, DASHBOARD]
    assert context.source == "datahub_mcp"
    assert context.assets[0].fields == ["customer_id", "lifetime_value"]
    assert context.assets[0].owners == ["Customer Data Platform"]
    assert context.assets[0].tags == ["Tier 1"]
    assert context.assets[0].quality_signals == ["uniqueness assertion", "daily freshness SLA"]
    assert context.assets[1].depends_on_fields == ["customer_id", "lifetime_value"]
    assert {(edge.source, edge.target) for edge in context.edges} == {
        (ROOT, FINANCE),
        (FINANCE, DASHBOARD),
    }
    assert provider.calls == [
        (
            "get_lineage",
            {"urn": ROOT, "upstream": False, "max_hops": 3, "max_results": 100},
        ),
        ("get_entities", {"urns": [ROOT, FINANCE, DASHBOARD]}),
        (
            "get_lineage",
            {"urn": DASHBOARD, "upstream": True, "max_hops": 1, "max_results": 100},
        ),
    ]
