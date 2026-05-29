from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "AI Power Blackout Predictor"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/blackout_predictor"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/blackout_predictor"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    OPENWEATHERMAP_API_KEY: str = ""
    SMS_GATEWAY_URL: str = "http://localhost:8001"
    SMS_GATEWAY_API_KEY: str = ""

    # Web Push VAPID keys — generate with: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.private_pem().decode()); print(v.public_key)"
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "mailto:admin@blackoutpredictor.com"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
