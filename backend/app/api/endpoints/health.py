from fastapi import APIRouter
from app.core.database import get_database
import logging

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint that also verifies database connectivity
    """
    try:
        db = await get_database()
        if db is not None:
            await db.command('ping')
            db_status = "connected"
        else:
            db_status = "disconnected"
            
        return {
            "status": "healthy",
            "database": db_status,
            "message": "API is running successfully"
        }
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "message": f"Health check failed: {str(e)}"
        }