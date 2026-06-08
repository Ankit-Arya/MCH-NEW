from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MCH KPI-6 Inspection Platform"
    ENVIRONMENT: str = "production"
    AUTO_CREATE_TABLES: bool = False
    API_PREFIX: str = "/api/v1"
    FRONTEND_ORIGIN: str = "http://localhost"

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+psycopg2://mch_user:mch_password@postgres:5432/mch_inspection"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "mch_minio_admin"
    MINIO_SECRET_KEY: str = "mch_minio_password"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "mch-inspections"
    MINIO_PUBLIC_BASE_URL: str | None = None

    MAX_PHOTO_MB: int = 8
    MAX_VIDEO_MB: int = 50
    MAX_VIDEO_SECONDS: int = 15

    KPI6_SM_WEIGHT: float = 0.6
    KPI6_EIT_WEIGHT: float = 0.4
    KPI6_THRESHOLD_PERCENT: float = 90
    KPI6_PENALTY_PERCENT: float = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
