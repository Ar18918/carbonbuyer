"""Buyer aggregation engine + repeat-buyer detection.

Recomputes, for every buyer, the roll-ups defined in the spec:
  total estimated volume, total retired, total non-retired, #projects,
  #countries, #project types, #purchase years, repeat purchase count,
  total repeat volume, repeat buyer score, and the one-time/repeat flag.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Buyer, BuyerProjectLink, Project


def _repeat_score(num_projects: int, num_years: int, num_countries: int, num_types: int) -> float:
    """0-100 composite. Rewards breadth across projects, years, geographies, types."""
    if num_projects <= 1:
        return 0.0
    score = (
        min(num_projects, 10) * 6      # up to 60
        + min(num_years, 6) * 4        # up to 24
        + min(num_countries, 4) * 2.5  # up to 10
        + min(num_types, 4) * 1.5      # up to 6
    )
    return round(min(score, 100.0), 1)


def recompute_all(db: Session) -> None:
    buyers = db.query(Buyer).all()
    for buyer in buyers:
        links = db.query(BuyerProjectLink).filter(BuyerProjectLink.buyer_id == buyer.id).all()

        total_est = sum(l.estimated_volume_tco2e or 0.0 for l in links)
        total_ret = sum(l.retirement_volume_tco2e or 0.0 for l in links)

        project_ids = {l.project_id for l in links}
        projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
        countries = {p.country for p in projects if p.country}
        types = {p.type for p in projects if p.type}
        years = {l.purchase_year for l in links if l.purchase_year}

        num_projects = len(project_ids)
        buyer.total_estimated_volume = round(total_est, 2)
        buyer.total_retired_volume = round(total_ret, 2)
        buyer.total_non_retired_volume = round(max(total_est - total_ret, 0.0), 2)
        buyer.num_projects = num_projects
        buyer.num_countries = len(countries)
        buyer.num_project_types = len(types)
        buyer.num_purchase_years = len(years)

        # A repeat buyer purchased from multiple projects OR across multiple years.
        is_repeat = num_projects > 1 or len(years) > 1
        buyer.is_repeat_buyer = is_repeat
        buyer.repeat_purchase_count = max(len(links) - 1, 0) if is_repeat else 0
        buyer.total_repeat_volume = round(total_est, 2) if is_repeat else 0.0
        buyer.repeat_buyer_score = _repeat_score(num_projects, len(years), len(countries), len(types))
    db.commit()
