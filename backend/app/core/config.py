from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Taranga ML Platform"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A FastAPI server with MongoDB integration for ML model management"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "taranga_db"
    
    # Security settings
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "file://",
        "*"  # Allow all origins for demo purposes
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()