import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from impactlint.fixtures import fixture_context
from impactlint.models import Asset, CatalogContext, GraphEdge, ReviewResponse


class CatalogProvider(ABC):
    @abstractmethod
    async def get_context(self, dataset_urn: str) -> CatalogContext:
        raise NotImplementedError

    @abstractmethod
    async def publish_review(self, review: ReviewResponse) -> str:
        raise NotImplementedError


class FixtureCatalogProvider(CatalogProvider):
    async def get_context(self, dataset_urn: str) -> CatalogContext:
        context = fixture_context()
        if dataset_urn != context.root_urn:
            raise LookupError(f"Dataset is not available in the demo catalog: {dataset_urn}")
        return context

    async def publish_review(self, review: ReviewResponse) -> str:
        return f"demo://datahub/documents/impactlint/{review.id}"


class DataHubMCPProvider(CatalogProvider):
    def __init__(self, url: str, token: str = "") -> None:
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}"} if token else None

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        async with create_mcp_http_client(headers=self.headers) as http_client:
            async with streamable_http_client(self.url, http_client=http_client) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments=arguments)

        texts = [getattr(item, "text", "") for item in result.content]
        payload = "\n".join(text for text in texts if text)
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"text": payload}

    async def get_context(self, dataset_urn: str) -> CatalogContext:
        lineage_payload = await self._call(
            "get_lineage",
            {"urn": dataset_urn, "upstream": False, "max_hops": 3, "max_results": 100},
        )
        asset_urns = list(dict.fromkeys([dataset_urn, *_asset_urns(lineage_payload)]))
        entity_payload = await self._call("get_entities", {"urns": asset_urns})
        assets = _normalize_assets(entity_payload, lineage_payload, dataset_urn)
        edges = _normalize_edges(lineage_payload, dataset_urn)

        known_urns = {asset.urn for asset in assets}
        deep_lineage_payloads: dict[str, Any] = {}
        for asset in assets:
            if asset.layer <= 1:
                continue
            upstream_payload = await self._call(
                "get_lineage",
                {"urn": asset.urn, "upstream": True, "max_hops": 1, "max_results": 100},
            )
            deep_lineage_payloads[asset.urn] = upstream_payload
            edges.extend(_direct_upstream_edges(upstream_payload, asset.urn, known_urns))

        if not assets:
            raise LookupError(f"DataHub returned no metadata for {dataset_urn}")
        return CatalogContext(
            root_urn=dataset_urn,
            assets=assets,
            edges=list({(edge.source, edge.target): edge for edge in edges}.values()),
            source="datahub_mcp",
            raw_evidence={
                "get_entities": entity_payload,
                "get_downstream_lineage": lineage_payload,
                "get_direct_upstreams": deep_lineage_payloads,
            },
        )

    async def publish_review(self, review: ReviewResponse) -> str:
        title = f"ImpactLint review: {review.target.name} ({review.id[:8]})"
        body = _review_markdown(review)
        result = await self._call(
            "save_document",
            {
                "document_type": "Analysis",
                "title": title,
                "content": body,
                "topics": ["impactlint", "schema-change", review.risk_level.value],
                "related_assets": [review.target.urn, *[asset.urn for asset in review.affected_assets]],
            },
        )
        await self._call(
            "add_tags",
            {
                "tag_urns": ["urn:li:tag:ImpactLintReviewed"],
                "entity_urns": [review.target.urn],
            },
        )
        return _find_first_string(result, ("urn", "url", "documentUrn")) or title


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _find_first_string(payload: Any, keys: tuple[str, ...]) -> str | None:
    for item in _walk(payload):
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            candidate = _find_first_string(item, ("name", "displayName", "fieldPath"))
            candidate = candidate or _find_first_string(item, ("urn",))
            if candidate:
                result.append(candidate)
    return list(dict.fromkeys(result))


def _is_asset_urn(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(
        ("urn:li:dataset:", "urn:li:dashboard:", "urn:li:chart:")
    )


def _asset_urns(payload: Any) -> list[str]:
    urns: list[str] = []
    for item in _walk(payload):
        urn = item.get("urn") or item.get("entityUrn")
        if _is_asset_urn(urn):
            urns.append(urn)
    return list(dict.fromkeys(urns))


def _urn_name(urn: str) -> str:
    components = urn.partition("(")[2].removesuffix(")").split(",")
    if urn.startswith("urn:li:dataset:") and len(components) >= 2:
        return components[-2]
    if components and components[-1]:
        return components[-1]
    return urn.rsplit(":", 1)[-1]


def _normalize_assets(entity_payload: Any, lineage_payload: Any, root_urn: str) -> list[Asset]:
    candidates: dict[str, dict[str, Any]] = {}
    for item in [*_walk(entity_payload), *_walk(lineage_payload)]:
        urn = item.get("urn") or item.get("entityUrn")
        if _is_asset_urn(urn):
            candidates.setdefault(urn, item)

    degrees = _lineage_degrees(lineage_payload)

    assets: list[Asset] = []
    for urn, item in candidates.items():
        properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
        schema = item.get("schemaMetadata") if isinstance(item.get("schemaMetadata"), dict) else {}
        ownership = item.get("ownership") if isinstance(item.get("ownership"), dict) else {}
        tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
        name = (
            item.get("name")
            or properties.get("name")
            or item.get("displayName")
            or item.get("qualifiedName")
            or item.get("dashboardId")
            or _urn_name(urn)
        )
        platform = item.get("platform") or item.get("platformName") or item.get("tool") or "DataHub"
        if isinstance(platform, dict):
            platform = platform.get("name") or platform.get("displayName") or "DataHub"
        assets.append(
            Asset(
                urn=urn,
                name=str(name),
                platform=str(platform),
                kind="dashboard" if urn.startswith(("urn:li:dashboard:", "urn:li:chart:")) else "dataset",
                layer=(
                    0
                    if urn == root_urn
                    else degrees.get(urn, int(item.get("degree") or item.get("hop") or 1))
                ),
                description=str(item.get("description") or properties.get("description") or ""),
                fields=_string_list(
                    item.get("schemaFields") or item.get("fields") or schema.get("fields")
                ),
                depends_on_fields=_custom_property_list(item, "impactlint.depends_on_fields"),
                owners=_string_list(item.get("owners") or ownership.get("owners")),
                tags=_string_list(tags.get("tags") if tags else item.get("tags")),
                quality_signals=(
                    _string_list(item.get("assertions") or item.get("quality"))
                    or _custom_property_list(item, "impactlint.quality_signals", separator="|")
                ),
            )
        )
    return assets


def _lineage_degrees(payload: Any) -> dict[str, int]:
    degrees: dict[str, int] = {}
    for item in _walk(payload):
        degree = item.get("degree")
        entity = item.get("entity")
        if not isinstance(degree, int) or not isinstance(entity, dict):
            continue
        urn = entity.get("urn")
        if isinstance(urn, str):
            degrees[urn] = degree
    return degrees


def _custom_property_list(item: dict[str, Any], key: str, separator: str = ",") -> list[str]:
    for nested in _walk(item):
        custom_properties = nested.get("customProperties")
        if isinstance(custom_properties, dict):
            value = custom_properties.get(key)
            if isinstance(value, str):
                return [part.strip() for part in value.split(separator) if part.strip()]
        if isinstance(custom_properties, list):
            for entry in custom_properties:
                if isinstance(entry, dict) and entry.get("key") == key:
                    value = entry.get("value")
                    if isinstance(value, str):
                        return [part.strip() for part in value.split(separator) if part.strip()]
    return []


def _normalize_edges(payload: Any, root_urn: str) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for item in _walk(payload):
        source = item.get("sourceUrn") or item.get("upstreamUrn") or item.get("source")
        target = item.get("targetUrn") or item.get("downstreamUrn") or item.get("target")
        if isinstance(source, dict):
            source = source.get("urn")
        if isinstance(target, dict):
            target = target.get("urn")
        if _is_asset_urn(source) and _is_asset_urn(target):
            edges.append(GraphEdge(source=source, target=target))

    for item in _walk(payload):
        entity = item.get("entity")
        degree = item.get("degree")
        if not isinstance(entity, dict) or degree != 1:
            continue
        urn = entity.get("urn") or entity.get("entityUrn")
        if _is_asset_urn(urn) and urn != root_urn:
            edges.append(GraphEdge(source=root_urn, target=urn))
    return list({(edge.source, edge.target): edge for edge in edges}.values())


def _direct_upstream_edges(payload: Any, target_urn: str, known_urns: set[str]) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for item in _walk(payload):
        entity = item.get("entity")
        if not isinstance(entity, dict) or item.get("degree") != 1:
            continue
        source_urn = entity.get("urn") or entity.get("entityUrn")
        if source_urn in known_urns and source_urn != target_urn:
            edges.append(GraphEdge(source=source_urn, target=target_urn))
    return edges


def _review_markdown(review: ReviewResponse) -> str:
    affected = "\n".join(f"- `{asset.name}` ({asset.platform})" for asset in review.affected_assets)
    signals = "\n".join(
        f"- **{signal.severity.value.upper()}**: {signal.title} — {signal.detail}"
        for signal in review.signals
    )
    return (
        f"# {review.headline}\n\n"
        f"Risk score: **{review.risk_score}/100**\n\n"
        f"{review.summary}\n\n"
        f"## Affected assets\n{affected}\n\n"
        f"## Evidence\n{signals}\n\n"
        f"Generated by ImpactLint review `{review.id}`."
    )
