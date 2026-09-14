from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.visual import VisualModulesResponse
from app.services.visual_modules import get_visual_modules


router = APIRouter(prefix="/visuals", tags=["visuals"])


@router.get("/modules", response_model=VisualModulesResponse)
def read_visual_modules(db: Session = Depends(get_db)) -> VisualModulesResponse:
    return get_visual_modules(db)
