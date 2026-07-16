"""Dashboard / analytics routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import DashboardResponse, ProjectFilters
from app.services import analytics as analytics_svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/dashboard", response_model=DashboardResponse)
def dashboard(f: ProjectFilters, source: str = Query("all", pattern="^(all|registry)$"),
              db: Session = Depends(get_db)):
    """The full dashboard payload (KPIs + all 13 visualizations + tables) for a segment.

    source=registry -> deterministic OffsetsDB retirement buyers only (fast, no AI).
    source=all      -> registry retirements + AI research findings.
    """
    return analytics_svc.build_dashboard(db, f, source=source)
