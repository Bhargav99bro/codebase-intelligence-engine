from fastapi import APIRouter
from app.api.v1.endpoints import (
    analyses,
    churn,
    compare,
    dependencies,
    duplication,
    exports,
    health,
    health_score,
    hotspots,
    issues,
    metrics,
    quality_gate,
    repositories,
    timeline,
    treemap,
)

api_v1_router = APIRouter()

# Mount endpoints
api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_v1_router.include_router(timeline.router, prefix="/repositories", tags=["Timeline"])
api_v1_router.include_router(compare.router, prefix="/analyses", tags=["Analysis Diff"])
api_v1_router.include_router(analyses.router, prefix="/analyses", tags=["Analyses"])
api_v1_router.include_router(metrics.router, prefix="/analyses", tags=["Metrics"])
api_v1_router.include_router(dependencies.router, prefix="/analyses", tags=["Dependencies"])
api_v1_router.include_router(issues.router, prefix="/analyses", tags=["Issues"])
api_v1_router.include_router(health_score.router, prefix="/analyses", tags=["Health Score"])
api_v1_router.include_router(treemap.router, prefix="/analyses", tags=["Treemap"])
api_v1_router.include_router(hotspots.router, prefix="/analyses", tags=["Hotspots"])
api_v1_router.include_router(quality_gate.router, prefix="/analyses", tags=["Quality Gate"])
api_v1_router.include_router(exports.router, prefix="/analyses", tags=["Exports"])
api_v1_router.include_router(duplication.router, prefix="/analyses", tags=["Duplication"])
api_v1_router.include_router(churn.router, prefix="/analyses", tags=["Git Churn"])

