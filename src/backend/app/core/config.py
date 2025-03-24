import os
from pydantic_settings import BaseSettings
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = "SECRET"
    FRONTEND_URL: str = ''
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    LICENSE_SERVER_VALIDATE_URL: str = ''

    PORT: int = 80
    RELOAD: bool = True


    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Check if the .env file exists
env_file_path = Path(".env")
if not env_file_path.exists():
    logger.warning("The .env file is missing. Falling back to OS environment variables.")

# Initialize settings
settings = Settings()
