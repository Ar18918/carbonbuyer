"""Database bootstrap + seeding.

Run:  python -m app.seed.seed_db

Steps:
  1. create tables
  2. create the bootstrap admin user (if none exist)
  3. ingest projects  (seed CSV if present, else the master workbook)
  4. load the researched buyer-intelligence snapshot (data/seed/*.json)
  5. recompute buyer aggregates
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import delete

from app.config import settings
from app.constants import tier_from_score
from app.db.base import Base
from app.db.models import Buyer, BuyerProjectLink, Project, ResearchRun, RiskFlag, User
from app.db.session import SessionLocal, engine
from app.etl.ingest_excel import ingest_from_csv, ingest_from_excel
from app.security import hash_password
from app.services import aggregation
from app.util import normalize_name

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed")


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_admin(db) -> None:
    if db.query(User).count() > 0:
        return
    db.add(User(email=settings.bootstrap_admin_email,
                hashed_password=hash_password(settings.bootstrap_admin_password),
                full_name="Platform Admin", role="admin"))
    db.commit()
    log.info("Created bootstrap admin: %s", settings.bootstrap_admin_email)


def ingest_projects(db) -> int:
    if os.path.exists(settings.seed_csv_path):
        return ingest_from_csv(db, settings.seed_csv_path)
    if os.path.exists(settings.excel_path):
        return ingest_from_excel(db, settings.excel_path, settings.projects_sheet)
    log.warning("No project source found (seed CSV or workbook).")
    return 0


def _upsert_buyer_from_profile(db, prof: dict) -> Buyer:
    name = prof["buyer_name"]
    key = normalize_name(name)
    b = db.query(Buyer).filter(Buyer.normalized_name == key).one_or_none()
    if not b:
        b = Buyer(name=name, normalized_name=key)
        db.add(b)
    b.aliases = prof.get("aliases", [])
    b.entity_type = prof.get("entity_type", "unknown")
    b.industry = prof.get("industry", "Other")
    b.industry_group = prof.get("industry_group", "")
    b.industry_confidence = prof.get("industry_confidence", "Low")
    b.hq_country = prof.get("hq_country")
    b.sbti_status = prof.get("sbti_status", "Unknown")
    b.sbti_near_term_status = prof.get("sbti_near_term_status")
    b.sbti_net_zero_status = prof.get("sbti_net_zero_status")
    b.sbti_validation_year = prof.get("sbti_validation_year")
    b.sbti_target_year = prof.get("sbti_target_year")
    b.sbti_alignment = prof.get("sbti_alignment", "Unknown")
    b.profile_summary = prof.get("profile_summary", "")
    b.source_urls = prof.get("source_urls", [])
    db.flush()
    return b


def load_research_snapshot(db) -> int:
    import glob as _glob
    files = sorted(_glob.glob(settings.seed_research_glob))
    if os.path.exists(settings.seed_research_path) and settings.seed_research_path not in files:
        files.append(settings.seed_research_path)
    if not files:
        log.warning("No research snapshots matching %s — buyer layer empty until a live run.",
                    settings.seed_research_glob)
        return 0

    # clear prior research once so re-seeding is idempotent, then load every snapshot
    db.execute(delete(BuyerProjectLink))
    db.execute(delete(RiskFlag))
    db.execute(delete(Buyer))
    db.commit()

    proj_by_pid = {p.project_id: p for p in db.query(Project).all()}
    total = 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("could not read snapshot %s: %s", path, exc)
            continue
        total += _load_one_snapshot(db, data, proj_by_pid)
    log.info("Loaded %d research snapshot(s): %d buyers, %d links", len(files), db.query(Buyer).count(), total)
    return total


def _load_one_snapshot(db, data: dict, proj_by_pid: dict) -> int:
    run = ResearchRun(
        country=data.get("segment", {}).get("country"),
        project_type=data.get("segment", {}).get("project_type"),
        params=data.get("segment", {}), status="completed", model="seed-snapshot",
        completed_at=datetime.now(timezone.utc))
    db.add(run)
    db.flush()

    for prof in data.get("buyer_profiles", []):
        _upsert_buyer_from_profile(db, prof)
    db.commit()

    n_links = 0
    for fnd in data.get("buyer_findings", []):
        proj = proj_by_pid.get(fnd.get("project_id"))
        if not proj:
            log.warning("finding references unknown project_id %s", fnd.get("project_id"))
            continue
        key = normalize_name(fnd["buyer_name"])
        buyer = db.query(Buyer).filter(Buyer.normalized_name == key).one_or_none()
        if not buyer:
            buyer = _upsert_buyer_from_profile(db, {"buyer_name": fnd["buyer_name"]})
        score = float(fnd.get("confidence_score", 0) or 0)
        tx = fnd.get("transaction_type", "unknown")
        vol = fnd.get("estimated_volume_tco2e")
        db.add(BuyerProjectLink(
            buyer_id=buyer.id, project_id=proj.id,
            buyer_role=fnd.get("buyer_role", "unknown"), transaction_type=tx,
            estimated_volume_tco2e=vol,
            retirement_volume_tco2e=(vol if tx == "retirement" else None),
            volume_basis=fnd.get("volume_basis"), purchase_year=fnd.get("purchase_year"),
            source_url=fnd.get("source_url", ""), source_type=fnd.get("source_type", "other"),
            evidence_summary=fnd.get("evidence_summary", ""),
            confidence_tier=fnd.get("confidence_tier") or tier_from_score(score),
            confidence_score=score, verdict=fnd.get("verdict"), research_run_id=run.id))
        n_links += 1

    for rk in data.get("risks", []):
        proj = proj_by_pid.get(rk.get("project_id"))
        if not proj:
            continue
        db.add(RiskFlag(
            project_id=proj.id, risk_category=rk.get("risk_category", ""),
            risk_description=rk.get("risk_description", ""),
            severity_score=float(rk.get("severity_score", 0) or 0),
            source_url=rk.get("source_url", ""), date=rk.get("date"),
            ai_summary=rk.get("ai_summary", ""), research_run_id=run.id))

    run.buyers_found = len(data.get("buyer_profiles", []))
    db.commit()
    return n_links


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        try:
            seed_admin(db)
        except Exception:
            log.exception("seed_admin failed — continuing with data load")
            db.rollback()
        n = ingest_projects(db)
        log.info("Projects in DB: %d", n)
        load_research_snapshot(db)
        aggregation.recompute_all(db)
        log.info("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
