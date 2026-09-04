from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InvestorAgent"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/investoragent.db"
    frontend_origin: str = "http://localhost:3000"
    log_level: str = "INFO"
    investoragent_user_agent: str = "InvestorAgent/0.1 contact@example.com"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    fred_api_key: str | None = None
    census_api_key: str | None = None
    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    newsapi_key: str | None = None
    gdelt_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
