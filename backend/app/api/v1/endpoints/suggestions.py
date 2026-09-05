from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.suggestion import ProactiveSuggestionsResponse
from app.services.suggestions import get_proactive_suggestions


router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/proactive", response_model=ProactiveSuggestionsResponse)
def read_proactive_suggestions(
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
) -> ProactiveSuggestionsResponse:
    return get_proactive_suggestions(db, limit=limit)
