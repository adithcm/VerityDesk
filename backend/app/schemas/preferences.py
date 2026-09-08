from pydantic import BaseModel, Field


class UserPreferencesUpdate(BaseModel):
    watchlist_tickers: list[str] | None = Field(default=None, max_length=50)
    preferred_regions: list[str] | None = Field(default=None, max_length=50)
    enabled_sources: list[str] | None = Field(default=None, max_length=50)


class UserPreferencesResponse(BaseModel):
    watchlist_tickers: list[str] = Field(default_factory=list)
    preferred_regions: list[str] = Field(default_factory=list)
    enabled_sources: list[str] = Field(default_factory=list)

