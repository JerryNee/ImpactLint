from impactlint.change_parser import parse_change
from impactlint.engine import affected_assets, context_payload, generate_artifacts, score_review
from impactlint.fixtures import SCENARIOS, fixture_context
from impactlint.models import Severity


def test_rename_finds_full_blast_radius_and_scores_critical() -> None:
    context = fixture_context()
    operations = parse_change(SCENARIOS[0].change_sql, SCENARIOS[0].dialect)
    affected = affected_assets(context, operations)
    score, level, signals = score_review(context, operations, affected)

    assert {asset.name for asset in affected} == {
        "finance.monthly_revenue",
        "ml.churn_features",
        "executive.revenue_overview",
        "growth.campaign_segments",
    }
    assert score == 100
    assert level == Severity.CRITICAL
    assert {signal.id for signal in signals} == {
        "breaking-change",
        "downstream-blast-radius",
        "governed-assets",
        "cross-team-coordination",
        "quality-contracts",
    }


def test_drop_generates_a_compatibility_guard_instead_of_a_fake_replacement() -> None:
    context = fixture_context()
    operations = parse_change(SCENARIOS[1].change_sql, SCENARIOS[1].dialect)
    affected = affected_assets(context, operations)
    artifacts = generate_artifacts(context.assets[0], operations, affected, 91)

    dbt_test = next(artifact for artifact in artifacts if artifact.kind == "dbt_tests")
    assert dbt_test.path == "artifacts/assert_lifetime_value_compatibility.sql"
    assert "select lifetime_value" in dbt_test.content
    assert "replacement field" not in dbt_test.rationale


def test_compression_context_keeps_canonical_evidence_and_segments_raw_mcp_data() -> None:
    context = fixture_context().model_copy(
        update={
            "source": "datahub_mcp",
            "raw_evidence": {
                "get_entities": [
                    {"urn": context_urn, "description": "raw envelope" * 500}
                    for context_urn in ("urn:li:dataset:a", "urn:li:dataset:b")
                ]
            },
        }
    )
    operations = parse_change(SCENARIOS[0].change_sql, SCENARIOS[0].dialect)
    affected = affected_assets(context, operations)
    _, _, signals = score_review(context, operations, affected)

    payload = context_payload(context, operations, affected, signals)

    assert len(payload.segments) >= 2
    assert all(line in payload.segments[0] for line in payload.required_lines)
    assert "WARNING LINEAGE" in payload.segments[0]
    assert "datahub.get_entities[0].urn" in "\n".join(payload.segments[1:])
