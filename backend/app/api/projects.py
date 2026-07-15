"""Project search + metadata routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import REDUCTION_REMOVAL_VALUES, REGISTRIES, REGISTRY_LABELS
from app.db.models import Project
from app.db.session import get_db
from app.schemas import ProjectFilters, ProjectOut
from app.services import filters as filter_svc

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/search", response_model=list[ProjectOut])
def search_projects(f: ProjectFilters, limit: int = 500, db: Session = Depends(get_db)):
    rows = filter_svc.query_projects(db, f).limit(limit).all()
    return [ProjectOut(
        id=p.id, project_id=p.project_id, project_name=p.project_name, registry=p.registry,
        voluntary_status=p.voluntary_status, scope=p.scope, type=p.type,
        reduction_removal=p.reduction_removal, methodology=p.methodology, region=p.region,
        country=p.country, state=p.state, developer=p.developer, credits_issued=p.credits_issued,
        credits_retired=p.credits_retired, credits_remaining=p.credits_remaining,
        first_vintage_year=p.first_vintage_year, is_eligible=p.is_eligible,
    ) for p in rows]


@router.get("/facets")
def facets(db: Session = Depends(get_db)):
    """Filter dropdown values, derived from the loaded dataset."""
    return {
        "countries": filter_svc.distinct_values(db, Project.country),
        "types": filter_svc.distinct_values(db, Project.type),
        "regions": filter_svc.distinct_values(db, Project.region),
        "registries": [{"value": r, "label": REGISTRY_LABELS.get(r, r)}
                       for r in REGISTRIES if r in set(filter_svc.distinct_values(db, Project.registry))],
        "reduction_removal": [v for v in REDUCTION_REMOVAL_VALUES
                              if v in set(filter_svc.distinct_values(db, Project.reduction_removal))],
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Project.id)).scalar() or 0
    eligible = db.query(func.count(Project.id)).filter(Project.is_eligible.is_(True)).scalar() or 0
    return {"total_projects": total, "eligible_projects": eligible}
