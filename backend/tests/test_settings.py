from app.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "InvestorAgent"
    assert settings.app_version == "0.1.0"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.cors_origins == ["http://localhost:3000"]


def test_cors_origins_support_comma_separated_values() -> None:
    settings = Settings(frontend_origin="http://localhost:3000, http://localhost:3001")

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:3001"]
