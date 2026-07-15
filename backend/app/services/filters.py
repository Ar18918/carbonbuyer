"""Project filtering — translates ProjectFilters into a SQLAlchemy query.

Applies the deterministic eligibility rules (status exclusions + vintage >= 2015)
unless the caller explicitly opts into including ineligible projects.
"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db.models import Project
from app.schemas import ProjectFilters


def query_projects(db: Session, f: ProjectFilters) -> Query:
    q = db.query(Project)

    if not f.include_ineligible:
        q = q.filter(Project.is_eligible.is_(True))

    if f.countries:
        q = q.filter(Project.country.in_(f.countries))
    elif f.country:
        q = q.filter(Project.country == f.country)
    if f.project_type:
        q = q.filter(Project.type == f.project_type)
    if f.registry:
        q = q.filter(Project.registry == f.registry)
    if f.region:
        q = q.filter(Project.region == f.region)
    if f.reduction_removal:
        q = q.filter(Project.reduction_removal == f.reduction_removal)

    if f.vintage_year_min is not None:
        q = q.filter(Project.first_vintage_year >= f.vintage_year_min)
    if f.vintage_year_max is not None:
        q = q.filter(Project.first_vintage_year <= f.vintage_year_max)

    if f.credits_issued_min is not None:
        q = q.filter(Project.credits_issued >= f.credits_issued_min)
    if f.credits_issued_max is not None:
        q = q.filter(Project.credits_issued <= f.credits_issued_max)
    if f.credits_retired_min is not None:
        q = q.filter(Project.credits_retired >= f.credits_retired_min)
    if f.credits_retired_max is not None:
        q = q.filter(Project.credits_retired <= f.credits_retired_max)

    if f.search:
        like = f"%{f.search.strip()}%"
        q = q.filter(or_(
            Project.project_name.ilike(like),
            Project.project_id.ilike(like),
            Project.developer.ilike(like),
        ))

    return q.order_by(Project.credits_issued.desc())


def distinct_values(db: Session, column) -> list[str]:
    rows = db.query(column).distinct().all()
    return sorted({(r[0] or "").strip() for r in rows if r[0]})
