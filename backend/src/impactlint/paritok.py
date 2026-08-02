from __future__ import annotations

import json
from typing import Any

import httpx
import tiktoken

from impactlint.models import CompressionMetrics


def count_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), sort_keys=True)
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


class ParitokClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def compress_context(
        self,
        context: dict[str, Any],
        query: str,
    ) -> tuple[str | None, CompressionMetrics]:
        serialized = json.dumps(context, separators=(",", ":"), sort_keys=True)
        original_tokens = count_tokens(serialized)
        if not self.configured:
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                source="Local token count; add a Paritok API key to measure hosted compression",
            )

        try:
            async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
                response = await client.post(
                    f"{self.base_url}/compress",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "content": serialized,
                        "query": query,
                        "kind": "other",
                        "upstream_model": "impactlint-reviewer",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                source=f"Paritok hosted GPU unavailable: {type(exc).__name__}",
            )

        payload = response.json()
        compressed = payload.get("compressed")
        if not payload.get("gpu_available") or not isinstance(compressed, str):
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                source=str(payload.get("message") or "Paritok returned no compressed context"),
            )

        compressed_tokens = count_tokens(compressed)
        saved = max(0, original_tokens - compressed_tokens)
        reduction = round((saved / original_tokens) * 100, 1) if original_tokens else 0.0
        return compressed, CompressionMetrics(
            status="measured",
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            tokens_saved=saved,
            reduction_percent=reduction,
            source="Paritok hosted GPU response; exact request and response token counts",
        )
