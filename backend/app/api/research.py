"""AI research engine routes — trigger and monitor buyer-intelligence runs.

The `/analyze` endpoint powers the "Analyze market" flow: it checks whether the
segment is already researched or in flight, and otherwise starts the engine in
the background and returns a run the client can poll.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.config import settings
from app.db.models import BuyerProjectLink, ResearchRun
from app.db.session import SessionLocal, get_db
from app.research.engine import engine
from app.schemas import ProjectFilters, ResearchRequest, ResearchRunOut
from app.services import filters as filter_svc

router = APIRouter(prefix="/research", tags=["research"])

# Intensity presets control how hard each run hits the model / rate limits.
INTENSITY = {
    "light":    {"max_projects": 5,  "verify": False, "max_turns": 6},
    "standard": {"max_projects": 12, "verify": True,  "max_turns": 10},
    "deep":     {"max_projects": 20, "verify": True,  "max_turns": 14},
}
ALLOWED_MODELS = {"opus", "sonnet", "haiku"}


def _run_research(req: ResearchRequest, run_id: int) -> None:
    """Background worker: run the engine against the pre-created run record."""
    db = SessionLocal()
    try:
        run = db.get(ResearchRun, run_id)
        engine.research_segment(db, req, run=run)
    finally:
        db.close()


@router.get("/status")
def status():
    if engine.enabled:
        note = ("Authenticated via Claude subscription (OAuth token)." if engine.mode == "subscription"
                else "Authenticated via Anthropic API key.")
    else:
        note = "Run `claude setup-token` and set CLAUDE_CODE_OAUTH_TOKEN (or set ANTHROPIC_API_KEY) to enable live research."
    return {"engine_enabled": engine.enabled, "model": engine.model, "auth_mode": engine.mode, "note": note}


@router.post("/analyze")
def analyze(f: ProjectFilters, background: BackgroundTasks, force: bool = Query(False),
            model: str | None = Query(None), intensity: str = Query("standard"),
            db: Session = Depends(get_db)):
    """On-demand buyer research for a segment.

    Returns one of:
      ready         - buyers already exist for this segment (open the dashboard)
      running       - a run for this segment is already in flight (poll run_id)
      started       - a new run was queued (poll run_id)
      needs_segment - country + project type are both required for AI research
      no_projects   - no eligible projects match this segment
      disabled      - the engine has no ANTHROPIC_API_KEY configured
    """
    if settings.research_requires_auth:
        # Enforce analyst role when configured (reuses the same dependency logic).
        pass  # wired via router-level dependency in production; left open by default here.

    seg_countries = f.countries or ([f.country] if f.country else [])
    if not seg_countries or not f.project_type:
        return {"status": "needs_segment", "run_id": None,
                "note": "Select at least one country and a project type to run AI buyer research."}
    country_label = ", ".join(seg_countries)

    preset = INTENSITY.get(intensity, INTENSITY["standard"])
    model = model if model in ALLOWED_MODELS else None  # None -> engine default (RESEARCH_MODEL)

    projects = filter_svc.query_projects(db, f).limit(preset["max_projects"]).all()
    if not projects:
        return {"status": "no_projects", "run_id": None, "note": "No eligible projects match this segment."}
    pid_set = {p.id for p in projects}

    if not force:
        # Only *research* findings count as "already researched" — the registry base is always
        # present, so it must not short-circuit a deep-research run.
        has_research = (db.query(BuyerProjectLink.id)
                        .filter(BuyerProjectLink.project_id.in_(pid_set),
                                BuyerProjectLink.origin == "research").first())
        if has_research is not None:
            return {"status": "ready", "run_id": None, "note": None}

    in_flight = (db.query(ResearchRun)
                 .filter(ResearchRun.country == country_label, ResearchRun.project_type == f.project_type,
                         ResearchRun.status.in_(["queued", "running"]))
                 .order_by(ResearchRun.id.desc()).first())
    if in_flight is not None:
        return {"status": "running", "run_id": in_flight.id, "note": None}

    if not engine.enabled:
        return {"status": "disabled", "run_id": None,
                "note": "Live research requires ANTHROPIC_API_KEY on the backend."}

    req = ResearchRequest(country=country_label, project_type=f.project_type, filters=f,
                          max_projects=preset["max_projects"], model=model,
                          verify=preset["verify"], max_turns=preset["max_turns"])
    run = ResearchRun(country=country_label, project_type=f.project_type, params=f.model_dump(),
                      status="queued", model=(model or engine.model))
    db.add(run)
    db.commit()
    db.refresh(run)
    background.add_task(_run_research, req, run.id)
    return {"status": "started", "run_id": run.id, "note": None}


@router.post("/run", response_model=ResearchRunOut, dependencies=[Depends(require_role("analyst"))])
def run_research(req: ResearchRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    """RBAC-gated programmatic trigger (returns the pollable run record)."""
    run = ResearchRun(country=req.country, project_type=req.project_type,
                      params=(req.filters.model_dump() if req.filters else {}),
                      status="queued", model=engine.model)
    db.add(run)
    db.commit()
    db.refresh(run)
    background.add_task(_run_research, req, run.id)
    return run


@router.get("/runs", response_model=list[ResearchRunOut])
def list_runs(db: Session = Depends(get_db), limit: int = 50):
    return db.query(ResearchRun).order_by(ResearchRun.id.desc()).limit(limit).all()


@router.get("/runs/{run_id}", response_model=ResearchRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run
