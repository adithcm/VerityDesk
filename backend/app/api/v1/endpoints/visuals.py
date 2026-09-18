from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.visual import VisualModulesResponse
from app.services.auth import optional_user_from_authorization, require_user
from app.services.visual_modules import get_visual_modules


router = APIRouter(prefix="/visuals", tags=["visuals"])


@router.get("/modules", response_model=VisualModulesResponse)
def read_visual_modules(
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> VisualModulesResponse:
    user = optional_user_from_authorization(db, authorization)
    return get_visual_modules(db, user_id=user.id if user else None)
