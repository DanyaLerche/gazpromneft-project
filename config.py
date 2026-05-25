from pydantic_settings import BaseSettings, SettingsConfigDict
import os
class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    JWT_SECRET_KEY: str = "change-me-access-secret"
    JWT_REFRESH_SECRET_KEY: str = "change-me-refresh-secret"
    JWT_ACCESS_TTL_MINUTES: int = 30
    JWT_REFRESH_TTL_DAYS: int = 30
    AUTH_PBKDF2_ITERATIONS: int = 200000
    AUTH_DEMO_PASSWORD: str = "demo12345"
    AUTH_DEV_ONE_PASSWORD: str = "12345"
    AUTH_EMAIL_VERIFICATION_TTL_MINUTES: int = 10
    AUTH_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    AUTH_EMAIL_VERIFICATION_SECRET: str = "change-me-email-verification-secret"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@task-tracker.local"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 15
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_ENDPOINT_URL: str | None = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "attachments"
    S3_USE_SSL: bool = False
    S3_PRESIGNED_UPLOAD_EXPIRES_SECONDS: int = 900
    S3_PRESIGNED_DOWNLOAD_EXPIRES_SECONDS: int = 900

    @property
    def DATABASE_URL(self):
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
