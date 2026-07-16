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

import csv
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


REGISTRY_BY_PREFIX = {
    "VCS": "Verra", "GS": "Gold Standard", "GLD": "Gold Standard",
    "CAR": "Climate Action Reserve", "ACR": "American Carbon Registry",
    "ART": "ART TREES", "ISO": "Isometric", "CCB": "Cercarbono",
}


def _registry_of(pid: str) -> str:
    up = pid.upper()
    for pre, name in REGISTRY_BY_PREFIX.items():
        if up.startswith(pre):
            return name
    return "the registry"


def _load_buyer_enrichment() -> dict:
    """name -> {industry, entity_type, sbti_status, sbti_alignment, sbti_target_year}
    (SBTi dataset match + curated industry map, precomputed offline)."""
    path = settings.seed_buyer_enrichment_csv
    out: dict = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[normalize_name(row.get("buyer_name", ""))] = row
    return out


def _upsert_registry_buyer(db, name: str, cache: dict, enrich: dict) -> Buyer:
    key = normalize_name(name)
    if key in cache:
        return cache[key]
    b = db.query(Buyer).filter(Buyer.normalized_name == key).one_or_none()
    if not b:  # only classify NEW buyers — never clobber a researched profile
        e = enrich.get(key, {})
        industry = (e.get("industry") or "Unknown").strip() or "Unknown"
        align = (e.get("sbti_alignment") or "Unknown").strip() or "Unknown"
        classified = industry not in ("Unknown", "Other")
        b = Buyer(
            name=name, normalized_name=key,
            entity_type=(e.get("entity_type") or "unknown").strip() or "unknown",
            industry=industry,
            industry_confidence=("Reference" if classified else "n/a"),
            sbti_status=(e.get("sbti_status") or "Unknown").strip() or "Unknown",
            sbti_alignment=align,
            sbti_target_year=((e.get("sbti_target_year") or "").strip() or None),
            profile_summary=("Identified from public registry retirement records. "
                             + ("SBTi status matched to the Science Based Targets initiative database. "
                                if align != "Unknown" else "")
                             + "Run Deep research for transaction roles (offtake/funding) and a fuller profile."),
            source_urls=["https://carbonplan.org/research/offsets-db"])
        db.add(b)
        db.flush()
    cache[key] = b
    return b


def load_registry_retirements(db) -> int:
    """Load the deterministic 'Registered buyers' layer: harmonized retirement beneficiaries
    (OffsetsDB) pre-matched to our project_ids. origin='registry', no AI involved."""
    path = settings.seed_registry_csv
    if not os.path.exists(path):
        log.info("No registry retirements seed at %s — registry buyer layer empty.", path)
        return 0
    db.execute(delete(BuyerProjectLink).where(BuyerProjectLink.origin == "registry"))  # idempotent
    db.commit()

    proj_by_pid = {p.project_id: p for p in db.query(Project).all()}
    enrich = _load_buyer_enrichment()
    cache: dict = {}

    def _num(s):
        try:
            return int(float(s)) if str(s).strip() else None
        except (TypeError, ValueError):
            return None

    # Accumulate per (buyer_id, project_id) so name-normalization collisions (e.g. "Shell"/"SHELL")
    # merge instead of violating the (buyer_id, project_id, source_url) unique constraint.
    acc: dict = {}
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            proj = proj_by_pid.get((row.get("project_id") or "").strip())
            name = (row.get("buyer_name") or "").strip()
            if not proj or not name:
                continue
            try:
                vol = float(row.get("retired_tco2e") or 0)
            except ValueError:
                vol = 0.0
            buyer = _upsert_registry_buyer(db, name, cache, enrich)
            key = (buyer.id, proj.id)
            fv, lv = _num(row.get("first_vintage")), _num(row.get("last_vintage"))
            ry = _num(row.get("last_retirement_year")) or _num(row.get("first_retirement_year"))
            a = acc.get(key)
            if a is None:
                acc[key] = {"vol": vol, "n": _num(row.get("txn_count")) or 1, "vmin": fv, "vmax": lv,
                            "ry": ry, "reg": _registry_of(proj.project_id),
                            "url": (row.get("source_url") or "").strip()}
            else:
                a["vol"] += vol
                a["n"] += _num(row.get("txn_count")) or 1
                a["vmin"] = fv if a["vmin"] is None else (min(a["vmin"], fv) if fv else a["vmin"])
                a["vmax"] = lv if a["vmax"] is None else (max(a["vmax"], lv) if lv else a["vmax"])
                if ry and (a["ry"] is None or ry > a["ry"]):
                    a["ry"] = ry

    for (bid, pid), a in acc.items():
        vintages = (f"{a['vmin']}–{a['vmax']}" if a["vmin"] and a["vmax"] and a["vmin"] != a["vmax"]
                    else str(a["vmin"] or a["vmax"] or ""))
        db.add(BuyerProjectLink(
            buyer_id=bid, project_id=pid,
            buyer_role="retirement_beneficiary", transaction_type="retirement",
            estimated_volume_tco2e=a["vol"], retirement_volume_tco2e=a["vol"],
            volume_basis="Registry retirement records (OffsetsDB harmonized beneficiary)",
            purchase_year=(str(a["ry"]) if a["ry"] else None),
            source_url=(a["url"] or "https://carbonplan.org/research/offsets-db"),
            source_type="registry-retirement",
            evidence_summary=(f"Retired {round(a['vol']):,} tCO2e across {a['n']} retirement(s)"
                              + (f" (vintages {vintages})" if vintages else "")
                              + f", per {a['reg']} registry records compiled by CarbonPlan OffsetsDB."),
            confidence_tier="High", confidence_score=95.0, verdict="CONFIRMED", origin="registry"))
    db.commit()
    log.info("Loaded %d registry retirement links across %d buyers.", len(acc), len(cache))
    return len(acc)


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
        load_registry_retirements(db)
        aggregation.recompute_all(db)
        log.info("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
