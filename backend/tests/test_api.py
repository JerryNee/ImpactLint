from fastapi.testclient import TestClient

from impactlint.catalog import FixtureCatalogProvider
from impactlint.fixtures import SCENARIOS
from impactlint.main import app, get_service
from impactlint.paritok import ParitokClient
from impactlint.service import ReviewService


def _demo_service() -> ReviewService:
    return ReviewService(
        FixtureCatalogProvider(),
        ParitokClient("http://localhost:8080", "", "gpt-4.1-mini", ""),
        "fixture",
    )


def test_create_and_publish_review() -> None:
    demo_service = _demo_service()
    app.dependency_overrides[get_service] = lambda: demo_service

    with TestClient(app) as client:
        response = client.post(
            "/api/reviews",
            json={
                "dataset_urn": SCENARIOS[0].dataset_urn,
                "change_sql": SCENARIOS[0].change_sql,
                "dialect": SCENARIOS[0].dialect,
            },
        )
        assert response.status_code == 200
        review = response.json()
        assert review["risk_level"] == "critical"
        assert len(review["affected_assets"]) == 4
        assert review["compression"]["status"] == "not_connected"

        publish = client.post(f"/api/reviews/{review['id']}/publish")
        assert publish.status_code == 200
        assert publish.json()["destination"].startswith("demo://datahub/documents/")

    app.dependency_overrides.clear()


def test_unknown_dataset_returns_validation_error() -> None:
    demo_service = _demo_service()
    app.dependency_overrides[get_service] = lambda: demo_service

    with TestClient(app) as client:
        response = client.post(
            "/api/reviews",
            json={
                "dataset_urn": "urn:li:dataset:missing",
                "change_sql": SCENARIOS[0].change_sql,
                "dialect": SCENARIOS[0].dialect,
            },
        )
        assert response.status_code == 422

    app.dependency_overrides.clear()
