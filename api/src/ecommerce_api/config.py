from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COMMERCE_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    tenant_id: str = "example"
    database_url: str = "postgresql://commerce:commerce@localhost:5432/commerce"
    api_key: str = Field(default="development-commerce-api-key-change-me", min_length=32)
    link_secret: str = Field(default="development-commerce-link-secret-change-me", min_length=32)
    currency: str = Field(default="ARS", pattern=r"^[A-Z]{3}$")
    pickup_location: str = "Retiro en el local"
    public_url: str = "http://localhost:8080"
    storefront_url: str = "http://localhost:3000"
    payments_url: str = ""
    payments_api_key: str = ""
    payments_callback_secret: str = ""
    callback_max_skew_seconds: int = Field(default=300, ge=30, le=900)
    abandonment_idle_minutes: int = Field(default=24 * 60, ge=15, le=30 * 24 * 60)
    abandonment_batch_size: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if self.payments_url and (
            len(self.payments_api_key) < 32 or len(self.payments_callback_secret) < 32
        ):
            raise ValueError("payment service credentials are incomplete")
        if self.environment == "production" and not self.public_url.startswith("https://"):
            raise ValueError("production public URL must use HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
