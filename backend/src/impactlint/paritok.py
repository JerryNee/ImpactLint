from __future__ import annotations

import json
from typing import Any

import httpx
import tiktoken

from impactlint.models import CompressionMetrics


def count_tokens(value: Any) -> int:
    text = json.dumps(value, separators=(",", ":"), sort_keys=True)
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


class ParitokClient:
    def __init__(self, base_url: str, api_key: str, model: str, llm_api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.llm_api_key = llm_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.llm_api_key)

    async def explain(self, context: dict[str, Any], prompt: str) -> tuple[str | None, CompressionMetrics]:
        original_tokens = count_tokens(context)
        if not self.configured:
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                source="Local token count; connect Paritok to measure compression",
            )

        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "X-Paritok-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            before = await _stats(client, self.base_url)
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You explain data-change risk using only the supplied evidence.",
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\n\nCATALOG CONTEXT:\n{json.dumps(context)}",
                        },
                    ],
                },
            )
            response.raise_for_status()
            after = await _stats(client, self.base_url)

        payload = response.json()
        explanation = payload["choices"][0]["message"]["content"]
        original_delta = max(
            0, after.get("input_tokens_original", 0) - before.get("input_tokens_original", 0)
        )
        compressed_delta = max(
            0,
            after.get("input_tokens_compressed", 0) - before.get("input_tokens_compressed", 0),
        )
        measured_original = original_delta or original_tokens
        saved = max(0, measured_original - compressed_delta)
        reduction = round((saved / measured_original) * 100, 1) if measured_original else 0.0
        return explanation, CompressionMetrics(
            status="measured",
            original_tokens=measured_original,
            compressed_tokens=compressed_delta,
            tokens_saved=saved,
            reduction_percent=reduction,
            source="Paritok proxy /stats delta",
        )


async def _stats(client: httpx.AsyncClient, base_url: str) -> dict[str, int]:
    response = await client.get(f"{base_url}/stats")
    response.raise_for_status()
    return response.json()
