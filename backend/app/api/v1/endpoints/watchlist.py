from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.watchlist import WatchEvaluationResponse, WatchItemCreate, WatchItemListResponse, WatchItemResponse, WatchItemUpdate
from app.services.watchlist import create_watch_item, delete_watch_item, evaluate_watch_items, list_watch_items, update_watch_item


router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/items", response_model=WatchItemListResponse)
def get_watch_items(db: Session = Depends(get_db)) -> WatchItemListResponse:
    return list_watch_items(db)


@router.post("/items", response_model=WatchItemResponse, status_code=status.HTTP_201_CREATED)
def add_watch_item(request: WatchItemCreate, db: Session = Depends(get_db)) -> WatchItemResponse:
    return create_watch_item(db, request)


@router.put("/items/{watch_item_id}", response_model=WatchItemResponse)
def edit_watch_item(
    watch_item_id: int,
    request: WatchItemUpdate,
    db: Session = Depends(get_db),
) -> WatchItemResponse:
    return update_watch_item(db, watch_item_id, request)


@router.delete("/items/{watch_item_id}")
def remove_watch_item(watch_item_id: int, db: Session = Depends(get_db)) -> dict[str, bool | int]:
    return delete_watch_item(db, watch_item_id)


@router.post("/evaluate", response_model=WatchEvaluationResponse)
def check_watch_items(db: Session = Depends(get_db)) -> WatchEvaluationResponse:
    return evaluate_watch_items(db)
