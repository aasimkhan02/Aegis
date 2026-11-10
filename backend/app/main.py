from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import (
    assistants,
    dashboard,
    datasets,
    demo_assistant,
    evaluations,
    health,
    projects,
    test_cases,
)

app = FastAPI(title="Aegis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(assistants.router, prefix="/api/assistants", tags=["assistants"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
app.include_router(test_cases.router, prefix="/api", tags=["test_cases"])
app.include_router(demo_assistant.router, prefix="/api/demo", tags=["demo_assistant"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])

