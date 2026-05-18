import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Rental House Platform"
    
    # Database
    POSTGRES_USER: str = Field("postgres", alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("postgres", alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("rental_db", alias="POSTGRES_DB")
    POSTGRES_HOST: str = Field("localhost", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, alias="POSTGRES_PORT")
    DATABASE_URL: str | None = None
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    
    # JWT Auth
    JWT_SECRET: str = Field("super-secret-key", alias="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_BUCKET_NAME: str | None = None
    AWS_REGION: str = "ap-southeast-1"
    
    # Firebase
    FCM_CREDENTIAL_PATH: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
