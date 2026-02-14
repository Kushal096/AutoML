from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import logging
from app.core.config import settings
from app.models import (
    User, System, Project, Dataset, Model, DriftMetric, DriftBaseline, DataColumn, TrainingLogs,
    FeatureDefinition, FeatureSet, FeatureValue, ModelRegistryMetadata
)

mongodb_client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    global mongodb_client, database
    try:
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = mongodb_client[settings.DATABASE_NAME]
        
        await mongodb_client.admin.command('ping')
        logging.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
        
        await init_beanie(
            database=database,
            document_models=[
                User, System, Project, Dataset, Model, DriftMetric, DriftBaseline, DataColumn, TrainingLogs,
                FeatureDefinition, FeatureSet, FeatureValue, ModelRegistryMetadata
            ] 
        )
        
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logging.info("Disconnected from MongoDB")


async def get_database():
    return database