from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.personalization import read_user_preferences, update_user_preferences


router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=UserPreferencesResponse)
def get_preferences(db: Session = Depends(get_db)) -> UserPreferencesResponse:
    return read_user_preferences(db)


@router.put("", response_model=UserPreferencesResponse)
def save_preferences(
    request: UserPreferencesUpdate,
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    return update_user_preferences(db, request)

