"""Saved searches (per-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import SavedSearch, User
from app.db.session import get_db
from app.schemas import SavedSearchIn, SavedSearchOut

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.get("", response_model=list[SavedSearchOut])
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SavedSearch).filter(SavedSearch.user_id == user.id).all()


@router.post("", response_model=SavedSearchOut)
def create_saved(payload: SavedSearchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = SavedSearch(user_id=user.id, name=payload.name, params=payload.params.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{sid}")
def delete_saved(sid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(SavedSearch, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(s)
    db.commit()
    return {"ok": True}
