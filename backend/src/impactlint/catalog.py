import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

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
        async with streamable_http_client(self.url, headers=self.headers) as streams:
            read_stream, write_stream, _ = streams
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
        entity_payload = await self._call("get_entities", {"urns": [dataset_urn]})
        lineage_payload = await self._call(
            "get_lineage",
            {"urn": dataset_urn, "direction": "downstream", "max_hops": 3},
        )
        assets = _normalize_assets(entity_payload, lineage_payload, dataset_urn)
        edges = _normalize_edges(lineage_payload, dataset_urn)
        if not assets:
            raise LookupError(f"DataHub returned no metadata for {dataset_urn}")
        return CatalogContext(
            root_urn=dataset_urn,
            assets=assets,
            edges=edges,
            source="datahub_mcp",
        )

    async def publish_review(self, review: ReviewResponse) -> str:
        title = f"ImpactLint review: {review.target.name} ({review.id[:8]})"
        body = _review_markdown(review)
        result = await self._call(
            "save_document",
            {
                "title": title,
                "content": body,
                "description": review.headline,
            },
        )
        await self._call(
            "add_tags",
            {"urns": [review.target.urn], "tags": ["ImpactLint Reviewed"]},
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
            candidate = _find_first_string(item, ("name", "displayName", "fieldPath", "urn"))
            if candidate:
                result.append(candidate)
    return list(dict.fromkeys(result))


def _normalize_assets(entity_payload: Any, lineage_payload: Any, root_urn: str) -> list[Asset]:
    candidates: dict[str, dict[str, Any]] = {}
    for item in [*_walk(entity_payload), *_walk(lineage_payload)]:
        urn = item.get("urn") or item.get("entityUrn")
        if isinstance(urn, str) and urn.startswith("urn:li:"):
            candidates.setdefault(urn, {}).update(item)

    assets: list[Asset] = []
    for urn, item in candidates.items():
        name = item.get("name") or item.get("displayName") or item.get("qualifiedName") or urn.split(",")[-2]
        platform = item.get("platform") or item.get("platformName") or "DataHub"
        if isinstance(platform, dict):
            platform = platform.get("name") or platform.get("displayName") or "DataHub"
        assets.append(
            Asset(
                urn=urn,
                name=str(name),
                platform=str(platform),
                layer=0 if urn == root_urn else int(item.get("degree") or item.get("hop") or 1),
                description=str(item.get("description") or ""),
                fields=_string_list(item.get("schemaFields") or item.get("fields")),
                owners=_string_list(item.get("owners")),
                tags=_string_list(item.get("tags")),
                quality_signals=_string_list(item.get("assertions") or item.get("quality")),
            )
        )
    return assets


def _normalize_edges(payload: Any, root_urn: str) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for item in _walk(payload):
        source = item.get("sourceUrn") or item.get("upstreamUrn") or item.get("source")
        target = item.get("targetUrn") or item.get("downstreamUrn") or item.get("target")
        if isinstance(source, dict):
            source = source.get("urn")
        if isinstance(target, dict):
            target = target.get("urn")
        if isinstance(source, str) and isinstance(target, str):
            edges.append(GraphEdge(source=source, target=target))

    if not edges:
        for item in _walk(payload):
            urn = item.get("urn") or item.get("entityUrn")
            if isinstance(urn, str) and urn.startswith("urn:li:") and urn != root_urn:
                edges.append(GraphEdge(source=root_urn, target=urn))
    return list({(edge.source, edge.target): edge for edge in edges}.values())


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
