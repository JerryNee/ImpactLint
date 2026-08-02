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
    context = {"assets": [{"name": "customer_360", "description": "shared profile" * 80}]}

    compressed, metrics = await client.compress_context(context, "Preserve high-risk evidence")

    assert compressed == "customer_id rename affects finance and ML owners"
    assert metrics.status == "measured"
    assert metrics.compressed_tokens == count_tokens(compressed)
    assert metrics.tokens_saved == metrics.original_tokens - metrics.compressed_tokens
    assert metrics.reduction_percent and metrics.reduction_percent > 0


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
