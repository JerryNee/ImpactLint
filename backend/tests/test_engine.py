from impactlint.change_parser import parse_change
from impactlint.engine import affected_assets, generate_artifacts, score_review
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
