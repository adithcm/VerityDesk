from pydantic import BaseModel, Field

from app.schemas.preferences import UserPreferencesResponse


class AuthProfile(BaseModel):
    profile_name: str = ""
    personal_note: str = ""
    location: str = ""
    housing_markets: str = ""
    watchlist: str = ""
    companies: str = ""
    priority_topics: list[str] = Field(default_factory=list)
    sectors: str = ""
    housing_interests: list[str] = Field(default_factory=list)
    macro_interests: list[str] = Field(default_factory=list)
    risk_preference: str = "balanced"
    investing_style: str = "long_term"
    answer_format: str = "brief"
    ignored_topics: str = ""
    briefing_style: str = "balanced"
    briefing_time: str = "08:00"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    setup_complete: bool
    preferences: UserPreferencesResponse
    profile: AuthProfile


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(AuthRequest):
    display_name: str = Field(min_length=1, max_length=120)


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    profile: AuthProfile
    setup_complete: bool = True
