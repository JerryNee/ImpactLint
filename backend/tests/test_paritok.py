import json

import httpx

from impactlint.paritok import ParitokClient, count_tokens


async def test_hosted_gpu_compression_reports_exact_savings() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://www.paritok.com/api/compress"
        assert request.headers["Authorization"] == "Bearer pk_test_impactlint"
        payload = json.loads(request.content)
        assert payload["model"] == "paritok-4b-v1"
        assert payload["query"].startswith("Preserve")
        assert "ml.churn_features" in payload["query"]
        assert payload["kind"] == "other"
        assert payload["upstream_model"] == "impactlint-reviewer"
        return httpx.Response(
            200,
            json={
                "compressed": "customer_id rename affects finance and ML owners",
                "gpu_available": True,
            },
        )

    client = ParitokClient(
        "https://www.paritok.com/api",
        "pk_test_impactlint",
        "paritok-4b-v1",
        transport=httpx.MockTransport(handler),
    )
    context = {
        "assets": [
            {
                "name": "customer_360",
                "description": "shared profile " * 80 + "ml.churn_features",
            }
        ]
    }

    compressed, metrics = await client.compress_context(
        context,
        "Preserve high-risk evidence",
        ["finance", "ml.churn_features"],
    )

    assert compressed and "customer_id rename affects finance and ML owners" in compressed
    assert "[IMPACTLINT IDENTIFIER GUARD]" in compressed
    assert "ml.churn_features" in compressed
    assert metrics.status == "measured"
    assert metrics.compressed_tokens == count_tokens(compressed)
    assert metrics.tokens_saved == metrics.original_tokens - metrics.compressed_tokens
    assert metrics.reduction_percent and metrics.reduction_percent > 0
    assert metrics.evidence_terms_checked == 2
    assert metrics.evidence_terms_restored == 1


async def test_extractive_guard_discards_rewrites_and_restores_evidence_lines() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["kind"] == "log_output"
        if payload["content"].startswith("IMPACTLINT"):
            compressed = "WARNING AFFECTED | name=asset_a\nWARNING AFFECTED | name=asset_b"
        else:
            compressed = "INFO RAW | path=0 | value=noise\nINVENTED | tier=0"
        return httpx.Response(200, json={"compressed": compressed, "gpu_available": True})

    client = ParitokClient(
        "https://www.paritok.com/api",
        "pk_test_impactlint",
        "paritok-4b-v1",
        transport=httpx.MockTransport(handler),
    )
    required_lines = [
        "IMPACTLINT REVIEW EVIDENCE",
        "WARNING AFFECTED | name=asset_a",
        "WARNING LINEAGE | source=asset_a | target=asset_b",
    ]
    raw_segment = "\n".join(
        f"INFO RAW | path={index} | value=noise" for index in range(40)
    )

    compressed, metrics = await client.compress_context(
        ["\n".join(required_lines), raw_segment],
        "Keep WARNING lines verbatim",
        ["asset_a", "asset_b"],
        required_lines=required_lines,
        kind="log_output",
    )

    assert compressed
    assert "INVENTED" not in compressed
    assert "WARNING AFFECTED | name=asset_b" not in compressed
    assert all(line in compressed for line in required_lines)
    assert metrics.status == "measured"
    assert metrics.source_lines_selected == 2
    assert metrics.evidence_lines_checked == 3
    assert metrics.evidence_lines_restored == 2
    assert metrics.evidence_terms_restored == 0


async def test_hosted_gpu_auth_failure_does_not_break_a_review() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(401, json={"message": "invalid key"}))
    client = ParitokClient(
        "https://www.paritok.com/api",
        "pk_bad",
        "paritok-4b-v1",
        transport=transport,
    )

    compressed, metrics = await client.compress_context({"asset": "customer_360"}, "Preserve")

    assert compressed is None
    assert metrics.status == "not_connected"
    assert "HTTPStatusError" in metrics.source
