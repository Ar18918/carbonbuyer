"""Buyer intelligence routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Buyer, BuyerProjectLink
from app.db.session import get_db
from app.schemas import BuyerLinkOut, BuyerOut

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.get("", response_model=list[BuyerOut])
def list_buyers(db: Session = Depends(get_db), limit: int = 200):
    return db.query(Buyer).order_by(Buyer.total_estimated_volume.desc()).limit(limit).all()


@router.get("/{buyer_id}", response_model=BuyerOut)
def get_buyer(buyer_id: int, db: Session = Depends(get_db)):
    b = db.get(Buyer, buyer_id)
    if not b:
        raise HTTPException(404, "Buyer not found")
    return b


@router.get("/{buyer_id}/links", response_model=list[BuyerLinkOut])
def buyer_links(buyer_id: int, db: Session = Depends(get_db)):
    return db.query(BuyerProjectLink).filter(BuyerProjectLink.buyer_id == buyer_id).all()
