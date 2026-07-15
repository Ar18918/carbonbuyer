"""Dashboard / analytics routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import DashboardResponse, ProjectFilters
from app.services import analytics as analytics_svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/dashboard", response_model=DashboardResponse)
def dashboard(f: ProjectFilters, db: Session = Depends(get_db)):
    """The full dashboard payload (KPIs + all 13 visualizations + tables) for a segment."""
    return analytics_svc.build_dashboard(db, f)
