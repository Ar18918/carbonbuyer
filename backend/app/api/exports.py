"""Download Centre — CSV exports + executive-summary generation.

Export 1: Buyer Intelligence Dataset
Export 2: Project Dataset (with risk flags)
Export 3: Buyer-Project Mapping (with source links + confidence)
Export 4: Executive Summary (AI-written markdown; render/print to PDF client-side)
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.db.models import BuyerProjectLink, RiskFlag
from app.db.session import get_db
from app.schemas import ProjectFilters
from app.services import analytics as analytics_svc
from app.services import filters as filter_svc

router = APIRouter(prefix="/exports", tags=["exports"])


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/buyers.csv")
def export_buyers(f: ProjectFilters, db: Session = Depends(get_db)):
    dash = analytics_svc.build_dashboard(db, f)
    rows = [{
        "buyer": b.name, "industry": b.industry, "entity_type": b.entity_type,
        "sbti_status": b.sbti_status, "sbti_alignment": b.sbti_alignment,
        "estimated_volume_tco2e": b.total_estimated_volume,
        "retired_volume_tco2e": b.total_retired_volume,
        "non_retired_volume_tco2e": b.total_non_retired_volume,
        "projects": b.num_projects, "countries": b.num_countries,
        "project_types": b.num_project_types, "purchase_years": b.num_purchase_years,
        "repeat_buyer": b.is_repeat_buyer, "repeat_score": b.repeat_buyer_score,
        "hq_country": b.hq_country or "",
    } for b in sorted(dash.top_buyers + dash.repeat_buyers, key=lambda x: x.total_estimated_volume, reverse=True)]
    # de-dup by buyer name preserving order
    seen, deduped = set(), []
    for r in rows:
        if r["buyer"] in seen:
            continue
        seen.add(r["buyer"]); deduped.append(r)
    return _csv_response(deduped, "buyer_intelligence.csv")


@router.post("/projects.csv")
def export_projects(f: ProjectFilters, db: Session = Depends(get_db)):
    projects = filter_svc.query_projects(db, f).all()
    pid_set = {p.id for p in projects}
    risk_map: dict[int, list[RiskFlag]] = {}
    for rk in (db.query(RiskFlag).filter(RiskFlag.project_id.in_(pid_set)).all() if pid_set else []):
        risk_map.setdefault(rk.project_id, []).append(rk)
    rows = [{
        "project_id": p.project_id, "project_name": p.project_name, "registry": p.registry,
        "type": p.type, "reduction_removal": p.reduction_removal, "country": p.country,
        "region": p.region, "status": p.voluntary_status, "vintage": p.first_vintage_year or "",
        "credits_issued": p.credits_issued, "credits_retired": p.credits_retired,
        "credits_remaining": p.credits_remaining, "developer": p.developer,
        "eligible": p.is_eligible,
        "risk_flags": "; ".join(f"{r.risk_category}({int(r.severity_score)})" for r in risk_map.get(p.id, [])),
    } for p in projects]
    return _csv_response(rows, "project_dataset.csv")


@router.post("/buyer-project-mapping.csv")
def export_mapping(f: ProjectFilters, db: Session = Depends(get_db)):
    projects = filter_svc.query_projects(db, f).all()
    pid_set = {p.id for p in projects}
    links = (db.query(BuyerProjectLink)
             .options(joinedload(BuyerProjectLink.buyer), joinedload(BuyerProjectLink.project))
             .filter(BuyerProjectLink.project_id.in_(pid_set)).all()) if pid_set else []
    rows = [{
        "project_id": l.project.project_id if l.project else "",
        "project_name": l.project.project_name if l.project else "",
        "buyer": l.buyer.name if l.buyer else "",
        "buyer_role": l.buyer_role, "transaction_type": l.transaction_type,
        "estimated_volume_tco2e": l.estimated_volume_tco2e or "",
        "purchase_year": l.purchase_year or "",
        "confidence_tier": l.confidence_tier, "confidence_score": l.confidence_score,
        "verdict": l.verdict or "", "source_type": l.source_type,
        "source_url": l.source_url, "evidence": l.evidence_summary,
    } for l in links]
    return _csv_response(rows, "buyer_project_mapping.csv")


@router.post("/executive-summary.md", response_class=PlainTextResponse)
def export_exec_summary(f: ProjectFilters, db: Session = Depends(get_db)):
    dash = analytics_svc.build_dashboard(db, f)
    k = dash.kpis
    seg = f"{f.country or 'All countries'} · {f.project_type or 'All project types'}"
    top = "\n".join(
        f"{i+1}. **{b.name}** — {b.total_estimated_volume:,.0f} tCO₂e "
        f"({b.industry}, SBTi: {b.sbti_alignment})"
        for i, b in enumerate(dash.top_buyers[:10])) or "_No buyers identified for this segment yet._"
    risks = "\n".join(
        f"- **{r.risk_category}** (severity {int(r.severity_score)}): {r.ai_summary} [source]({r.source_url})"
        for r in sorted(dash.risks, key=lambda x: x.severity_score, reverse=True)[:8]) or "_No material red flags surfaced._"

    md = f"""# Carbon Credit Buyer Intelligence — Executive Summary

**Segment:** {seg}
**Projects included:** {k.total_projects}  |  **Buyers identified:** {k.total_buyers}
**Estimated buyer volume:** {k.total_estimated_volume:,.0f} tCO₂e
**Repeat buyers:** {k.repeat_buyer_pct}%  |  **SBTi-aligned buyers:** {k.sbti_aligned_pct}%

## Market Overview
This segment covers {k.total_projects} eligible offset projects. The buyer intelligence below is
compiled from public retirement disclosures, registry records, corporate & ESG reports, press
releases and program materials, each carrying a source link and confidence tier.

## Top Buyers
{top}

## Buyer Trends
- One-time vs repeat mix: {int(dash.buyer_frequency[0].value)} one-time / {int(dash.buyer_frequency[1].value)} repeat.
- Retirement split: {dash.retirement_split[0].value:,.0f} tCO₂e retired vs {dash.retirement_split[1].value:,.0f} tCO₂e held.

## SBTi Analysis
{"; ".join(f"{x.name}: {int(x.value)}" for x in dash.sbti_alignment)}

## Key Risks
{risks}

---
*Generated by the Carbon Credit Buyer Intelligence Platform. Every buyer claim is traceable to a
cited source and confidence score in the Buyer-Project Mapping export.*
"""
    return md
