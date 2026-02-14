from fastapi import APIRouter
from app.api.endpoints import (
    health, auth, systems, projects, training, datasets, 
    predictions, monitoring, features, model_registry, dashboard, assistant
)

api_router = APIRouter()

# Include individual endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(systems.router, tags=["systems"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(training.router, tags=["training"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(predictions.router, tags=["predictions"])
api_router.include_router(monitoring.router, tags=["monitoring"])
api_router.include_router(features.router, tags=["feature-store"])
api_router.include_router(model_registry.router, tags=["model-registry"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(assistant.router, tags=["assistant"])
