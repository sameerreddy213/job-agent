"""job-agent backend — Phase 4 (observability + dashboard backend APIs).

Wires structured JSON logging, request middleware, /metrics, and all routers.
Routes are served at root; Nginx exposes them under /api/ externally.
"""
from fastapi import FastAPI

from .api import (
    admin,
    analytics,
    applications,
    audit,
    auth,
    dashboard,
    health,
    jobs,
    materials,
    metrics,
    profile,
    queue,
    resumes,
    settings,
    sources,
    workflow,
)
from .logging_config import configure_logging
from .middleware import RequestLoggingMiddleware

configure_logging(service="api")

app = FastAPI(title="job-agent API", version="0.4.0-phase4")
app.add_middleware(RequestLoggingMiddleware)

# Core (Phase 1-2)
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(sources.router)
app.include_router(jobs.router)
app.include_router(materials.router)
app.include_router(admin.router)

# Dashboard backend (Phase 3)
app.include_router(queue.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(settings.router)
app.include_router(audit.router)
app.include_router(workflow.router)

# Application engine (Phase 8A)
app.include_router(applications.router)
