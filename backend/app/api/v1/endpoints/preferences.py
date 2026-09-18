from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.auth import current_user_from_authorization, require_user
from app.services.personalization import read_user_preferences, update_user_preferences


router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=UserPreferencesResponse)
def get_preferences(
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    user = current_user_from_authorization(db, authorization)
    return read_user_preferences(db, user)


@router.put("", response_model=UserPreferencesResponse)
def save_preferences(
    request: UserPreferencesUpdate,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    user = current_user_from_authorization(db, authorization)
    return update_user_preferences(db, request, user)
