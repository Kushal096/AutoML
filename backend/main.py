from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import api_router
from app.services import seed_systems
from app.services.dataset_service import DatasetService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await connect_to_mongo()
    
    # Seed systems on startup
    try:
        await seed_systems()
        logger.info("Systems seeded successfully")
    except Exception as e:
        logger.error(f"Failed to seed systems: {e}")
    
    # Clean up old temporary files on startup
    try:
        deleted_count = await DatasetService.cleanup_old_files(max_age_hours=24)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old temporary files")
    except Exception as e:
        logger.error(f"Failed to cleanup old files: {e}")
    
    yield
    logger.info("Shutting down...")
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "version": settings.VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )