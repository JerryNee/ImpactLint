from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from impactlint.catalog import DataHubMCPProvider, FixtureCatalogProvider
from impactlint.fixtures import SCENARIOS
from impactlint.models import Integration, PublishResponse, ReviewRequest, ReviewResponse, Scenario
from impactlint.paritok import ParitokClient
from impactlint.service import ReviewService
from impactlint.settings import Settings, get_settings


def create_service(settings: Settings) -> ReviewService:
    if settings.impactlint_mode == "datahub":
        catalog = DataHubMCPProvider(settings.datahub_mcp_url, settings.datahub_mcp_token)
    else:
        catalog = FixtureCatalogProvider()
    paritok = ParitokClient(
        settings.paritok_api_url,
        settings.paritok_api_key,
        settings.paritok_model,
    )
    return ReviewService(catalog, paritok, settings.impactlint_mode)


settings = get_settings()
service = create_service(settings)
app = FastAPI(
    title="ImpactLint API",
    version="0.1.0",
    description="Metadata-aware data change reviews powered by DataHub and Paritok.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> ReviewService:
    return service


ReviewServiceDependency = Annotated[ReviewService, Depends(get_service)]


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.impactlint_mode}


@app.get("/api/scenarios", response_model=list[Scenario])
async def scenarios() -> list[Scenario]:
    return SCENARIOS


@app.get("/api/integrations", response_model=list[Integration])
async def integrations(review_service: ReviewServiceDependency) -> list[Integration]:
    return review_service.integrations()


@app.post("/api/reviews", response_model=ReviewResponse)
async def create_review(
    request: ReviewRequest,
    review_service: ReviewServiceDependency,
) -> ReviewResponse:
    try:
        return await review_service.create_review(request)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    review_service: ReviewServiceDependency,
) -> ReviewResponse:
    try:
        return review_service.get_review(review_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/reviews/{review_id}/publish", response_model=PublishResponse)
async def publish_review(
    review_id: str,
    review_service: ReviewServiceDependency,
) -> PublishResponse:
    try:
        _, destination = await review_service.publish(review_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PublishResponse(review_id=review_id, status="published", destination=destination)


frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend(path: str) -> FileResponse:
        candidate = frontend_dist / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
