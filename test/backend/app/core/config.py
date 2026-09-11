from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "T1 HR-Case RecSys API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "hr_rec_db"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # MongoDB
    MONGO_URI: str = "mongodb://root:rootpassword@mongo:27017/?authSource=admin"
    MONGO_DB: str = "hr_raw_docs"

    # RecSys / NLP
    EMBEDDING_MODEL: str = "cointegrated/rubert-tiny2"
    EMBEDDING_DIM: int = 312  # rubert-tiny2 produces 312 dimensions; e5-small produces 384

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
