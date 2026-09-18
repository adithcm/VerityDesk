from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AuthResponse, ProfileUpdateRequest, RegisterRequest, AuthRequest, UserResponse
from app.services.auth import (
    authenticate_user,
    create_user,
    current_user_from_authorization,
    require_user,
    revoke_token,
    user_to_response,
)
from app.services.personalization import get_or_create_preferences


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, token = create_user(db, email=request.email, password=request.password, display_name=request.display_name)
    return AuthResponse(token=token, user=user_to_response(db, user))


@router.post("/login", response_model=AuthResponse)
def login(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, token = authenticate_user(db, email=request.email, password=request.password)
    return AuthResponse(token=token, user=user_to_response(db, user))


@router.get("/me", response_model=UserResponse)
def me(
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = current_user_from_authorization(db, authorization)
    return user_to_response(db, user)


@router.put("/profile", response_model=UserResponse)
def update_profile(
    request: ProfileUpdateRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = current_user_from_authorization(db, authorization)
    settings = get_or_create_preferences(db, user)
    settings.profile_metadata = request.profile.model_dump()
    settings.watchlist_tickers = [item.strip().upper() for item in request.profile.watchlist.split(",") if item.strip()]
    settings.preferred_regions = [
        item.strip()
        for item in [request.profile.location, *request.profile.housing_markets.split(",")]
        if item.strip()
    ]
    settings.daily_briefing_time = request.profile.briefing_time
    user.setup_complete = request.setup_complete
    db.commit()
    db.refresh(user)
    return user_to_response(db, user)


@router.post("/logout")
def logout(
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    revoke_token(db, authorization)
    return {"ok": True}
