from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
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
        context: dict[str, Any] | str | Sequence[str],
        query: str,
        required_terms: list[str] | None = None,
        required_lines: Sequence[str] | None = None,
        kind: str = "other",
    ) -> tuple[str | None, CompressionMetrics]:
        serialized_segments = _serialize_segments(context)
        original_tokens = sum(count_tokens(segment) for segment in serialized_segments)
        protected_terms = list(dict.fromkeys(term for term in (required_terms or []) if term))
        protected_lines = list(dict.fromkeys(line for line in (required_lines or []) if line))
        if not self.configured:
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                evidence_lines_checked=len(protected_lines),
                evidence_terms_checked=len(protected_terms),
                source="Local token count; add a Paritok API key to measure hosted compression",
            )

        async def compress_segment(client: httpx.AsyncClient, segment: str) -> dict[str, Any]:
            segment_terms = [term for term in protected_terms if term.lower() in segment.lower()]
            protected_suffix = ""
            if segment_terms:
                protected_suffix = "\nPreserve these exact evidence values: " + "; ".join(
                    segment_terms
                )
            response = await client.post(
                f"{self.base_url}/compress",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "content": segment,
                    "query": query + protected_suffix,
                    "kind": kind,
                    "upstream_model": "impactlint-reviewer",
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Paritok returned a non-object response")
            return payload

        try:
            async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
                payloads = await asyncio.gather(
                    *(compress_segment(client, segment) for segment in serialized_segments)
                )
        except (httpx.HTTPError, ValueError) as exc:
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                evidence_lines_checked=len(protected_lines),
                evidence_terms_checked=len(protected_terms),
                source=f"Paritok hosted GPU unavailable: {type(exc).__name__}",
            )

        compressed_segments: list[str] = []
        for payload in payloads:
            compressed = payload.get("compressed")
            if payload.get("gpu_available") and isinstance(compressed, str):
                compressed_segments.append(compressed)
                continue
            return None, CompressionMetrics(
                status="not_connected",
                original_tokens=original_tokens,
                evidence_lines_checked=len(protected_lines),
                evidence_terms_checked=len(protected_terms),
                source=str(payload.get("message") or "Paritok returned no compressed context"),
            )

        model_output = "\n".join(segment.rstrip() for segment in compressed_segments if segment)
        model_output_tokens = count_tokens(model_output)
        if protected_lines:
            compressed, selected_count, missing_lines = _extractive_guard(
                serialized_segments,
                compressed_segments,
                protected_lines,
            )
        else:
            compressed = model_output
            selected_count = 0
            missing_lines = []

        missing_terms = [term for term in protected_terms if term.lower() not in compressed.lower()]
        if missing_terms:
            compressed = (
                compressed.rstrip()
                + "\n\n[IMPACTLINT IDENTIFIER GUARD]\n"
                + "\n".join(f"- {term}" for term in missing_terms)
            )

        compressed_tokens = count_tokens(compressed)
        saved = max(0, original_tokens - compressed_tokens)
        reduction = round((saved / original_tokens) * 100, 1) if original_tokens else 0.0
        return compressed, CompressionMetrics(
            status="measured",
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            model_output_tokens=model_output_tokens,
            tokens_saved=saved,
            reduction_percent=reduction,
            source_lines_selected=selected_count,
            evidence_lines_checked=len(protected_lines),
            evidence_lines_restored=len(missing_lines),
            evidence_terms_checked=len(protected_terms),
            evidence_terms_restored=len(missing_terms),
            source=(
                "Paritok hosted GPU plus extractive evidence guard; exact input, model-output, "
                f"and final token counts; restored {len(missing_lines)} lines and "
                f"{len(missing_terms)} identifiers"
            ),
        )


def _serialize_segments(context: dict[str, Any] | str | Sequence[str]) -> list[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, dict):
        return [json.dumps(context, indent=2, sort_keys=True)]
    segments = [segment for segment in context if segment]
    return segments or [""]


def _extractive_guard(
    source_segments: Sequence[str],
    compressed_segments: Sequence[str],
    required_lines: Sequence[str],
) -> tuple[str, int, list[str]]:
    source_lines: dict[str, str] = {}
    for segment in source_segments:
        for line in segment.splitlines():
            normalized = line.strip()
            if normalized:
                source_lines.setdefault(normalized, normalized)

    selected: list[str] = []
    selected_set: set[str] = set()
    for segment in compressed_segments:
        for line in segment.splitlines():
            normalized = line.strip()
            if normalized in source_lines and normalized not in selected_set:
                selected.append(source_lines[normalized])
                selected_set.add(normalized)

    missing_lines = [line for line in required_lines if line not in selected_set]
    if missing_lines:
        selected.extend(["", "[IMPACTLINT EVIDENCE GUARD]", *missing_lines])
    return "\n".join(selected).strip(), len(selected_set), missing_lines
