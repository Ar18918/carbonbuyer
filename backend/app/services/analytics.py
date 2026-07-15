"""Analytics service — assembles the full dashboard payload for a segment.

All buyer metrics are computed *segment-scoped*: only the buyer-project evidence
links whose project falls inside the current filter set contribute. Buyer
attributes (industry, SBTi) are entity-level.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.constants import humanize_risk, tier_from_score
from app.db.models import BuyerProjectLink, Project, RiskFlag
from app.schemas import (
    BuyerOut, DashboardResponse, KPIs, NameValue, NameValue2, ProjectFilters,
    ProjectOut, RiskFlagOut,
)
from app.services import filters as filter_svc


def _nv(d: dict, top: int | None = None, reverse: bool = True) -> list[NameValue]:
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=reverse)
    if top:
        items = items[:top]
    return [NameValue(name=str(k), value=round(float(v), 2)) for k, v in items]


def build_dashboard(db: Session, f: ProjectFilters) -> DashboardResponse:
    projects: list[Project] = filter_svc.query_projects(db, f).all()
    pid_set = {p.id for p in projects}

    links: list[BuyerProjectLink] = []
    if pid_set:
        links = (
            db.query(BuyerProjectLink)
            .options(joinedload(BuyerProjectLink.buyer), joinedload(BuyerProjectLink.project))
            .filter(BuyerProjectLink.project_id.in_(pid_set))
            .all()
        )

    # --- per-buyer segment aggregation ---
    by_buyer: dict[int, dict] = {}
    for l in links:
        b = l.buyer
        agg = by_buyer.setdefault(b.id, {
            "buyer": b, "vol": 0.0, "ret": 0.0, "projects": set(), "years": set(),
            "countries": set(), "types": set(), "conf": 0.0,
        })
        agg["vol"] += l.estimated_volume_tco2e or 0.0
        agg["ret"] += l.retirement_volume_tco2e or 0.0
        agg["conf"] = max(agg["conf"], l.confidence_score or 0.0)  # best evidence tier for this buyer
        agg["projects"].add(l.project_id)
        if l.purchase_year:
            agg["years"].add(l.purchase_year)
        if l.project:
            if l.project.country:
                agg["countries"].add(l.project.country)
            if l.project.type:
                agg["types"].add(l.project.type)

    buyer_rows: list[BuyerOut] = []
    for agg in by_buyer.values():
        b = agg["buyer"]
        n_proj = len(agg["projects"])
        n_years = len(agg["years"])
        is_repeat = n_proj > 1 or n_years > 1
        buyer_rows.append(BuyerOut(
            id=b.id, name=b.name, entity_type=b.entity_type, industry=b.industry,
            industry_group=b.industry_group, industry_confidence=b.industry_confidence,
            hq_country=b.hq_country, sbti_status=b.sbti_status, sbti_alignment=b.sbti_alignment,
            sbti_validation_year=b.sbti_validation_year, sbti_target_year=b.sbti_target_year,
            profile_summary=b.profile_summary, source_urls=b.source_urls or [],
            total_estimated_volume=round(agg["vol"], 2), total_retired_volume=round(agg["ret"], 2),
            total_non_retired_volume=round(max(agg["vol"] - agg["ret"], 0.0), 2),
            num_projects=n_proj, num_countries=len(agg["countries"]),
            num_project_types=len(agg["types"]), num_purchase_years=n_years,
            repeat_purchase_count=max(n_proj - 1, 0) if is_repeat else 0,
            total_repeat_volume=round(agg["vol"], 2) if is_repeat else 0.0,
            repeat_buyer_score=b.repeat_buyer_score, is_repeat_buyer=is_repeat,
            confidence_score=round(agg["conf"], 1), confidence_tier=tier_from_score(agg["conf"]),
        ))

    buyer_rows.sort(key=lambda x: x.total_estimated_volume, reverse=True)
    total_vol = sum(r.total_estimated_volume for r in buyer_rows)
    total_ret = sum(r.total_retired_volume for r in buyer_rows)
    repeat_rows = [r for r in buyer_rows if r.is_repeat_buyer]

    # --- KPIs ---
    n_buyers = len(buyer_rows)
    repeat_pct = round(100.0 * len(repeat_rows) / n_buyers, 1) if n_buyers else 0.0
    aligned = len([r for r in buyer_rows if r.sbti_alignment == "SBTi Aligned"])
    sbti_pct = round(100.0 * aligned / n_buyers, 1) if n_buyers else 0.0
    kpis = KPIs(total_buyers=n_buyers, total_estimated_volume=round(total_vol, 2),
                total_projects=len(projects), repeat_buyer_pct=repeat_pct, sbti_aligned_pct=sbti_pct)

    # --- volume-attribution charts (attribute each link's volume to its project's attribute) ---
    by_region, by_country, by_rr, by_registry = (defaultdict(float) for _ in range(4))
    by_vintage, by_retyear = defaultdict(float), defaultdict(float)
    for l in links:
        vol = l.estimated_volume_tco2e or 0.0
        p = l.project
        if p:
            by_region[p.region or "Unknown"] += vol
            by_country[p.country or "Unknown"] += vol
            by_rr[p.reduction_removal or "Unknown"] += vol
            by_registry[p.registry or "Unknown"] += vol
            vint = str(p.first_vintage_year) if p.first_vintage_year else "Forward / pre-issuance"
            by_vintage[vint] += vol
        by_retyear[l.purchase_year or "Undisclosed"] += (l.retirement_volume_tco2e or l.estimated_volume_tco2e or 0.0)

    # --- SBTi + industry ---
    sbti_counts: dict[str, float] = defaultdict(float)
    for r in buyer_rows:
        sbti_counts[r.sbti_alignment] += 1
    for key in ("SBTi Aligned", "Not SBTi Aligned", "Unknown"):
        sbti_counts.setdefault(key, 0)

    ind_count: dict[str, float] = defaultdict(float)
    ind_vol: dict[str, float] = defaultdict(float)
    for r in buyer_rows:
        ind_count[r.industry] += 1
        ind_vol[r.industry] += r.total_estimated_volume
    industry_seg = [NameValue2(name=k, value=ind_count[k], value2=round(ind_vol[k], 2))
                    for k in sorted(ind_count, key=lambda k: ind_count[k], reverse=True)]

    freq = [NameValue(name="One-time buyers", value=n_buyers - len(repeat_rows)),
            NameValue(name="Repeat buyers", value=len(repeat_rows))]
    ret_split = [NameValue(name="Retired", value=round(total_ret, 2)),
                 NameValue(name="Non-retired", value=round(max(total_vol - total_ret, 0.0), 2))]

    # --- projects + risks ---
    risk_by_proj: dict[int, int] = defaultdict(int)
    buyercount_by_proj: dict[int, int] = defaultdict(int)
    for l in links:
        buyercount_by_proj[l.project_id] += 1
    risks = db.query(RiskFlag).filter(RiskFlag.project_id.in_(pid_set)).all() if pid_set else []
    top_risk_by_proj: dict[int, RiskFlag] = {}   # highest-severity researched risk per project
    for rk in risks:
        risk_by_proj[rk.project_id] += 1
        cur = top_risk_by_proj.get(rk.project_id)
        if cur is None or (rk.severity_score or 0) > (cur.severity_score or 0):
            top_risk_by_proj[rk.project_id] = rk

    project_out = []
    for p in projects:
        top = top_risk_by_proj.get(p.id)
        project_out.append(ProjectOut(
            id=p.id, project_id=p.project_id, project_name=p.project_name, registry=p.registry,
            voluntary_status=p.voluntary_status, scope=p.scope, type=p.type,
            reduction_removal=p.reduction_removal, methodology=p.methodology, region=p.region,
            country=p.country, state=p.state, developer=p.developer, credits_issued=p.credits_issued,
            credits_retired=p.credits_retired, credits_remaining=p.credits_remaining,
            first_vintage_year=p.first_vintage_year, is_eligible=p.is_eligible,
            risk_count=risk_by_proj.get(p.id, 0), buyer_count=buyercount_by_proj.get(p.id, 0),
            primary_risk=humanize_risk(top.risk_category) if top else None,
            primary_risk_severity=round(top.severity_score, 1) if top else None,
        ))

    return DashboardResponse(
        filters=f, kpis=kpis, buyer_count=n_buyers,
        top_buyers=buyer_rows[:20], repeat_buyers=sorted(repeat_rows, key=lambda x: x.total_estimated_volume, reverse=True)[:10],
        buyer_frequency=freq,
        vintage_activity=_nv(by_vintage),
        retirement_activity=_nv(by_retyear),
        retirement_split=ret_split,
        volume_by_region=_nv(by_region),
        volume_by_country=_nv(by_country, top=15),
        volume_by_reduction_removal=_nv(by_rr),
        volume_by_registry=_nv(by_registry),
        sbti_alignment=[NameValue(name=k, value=sbti_counts[k]) for k in ("SBTi Aligned", "Not SBTi Aligned", "Unknown")],
        industry_segmentation=industry_seg,
        projects=project_out,
        risks=[RiskFlagOut.model_validate(r) for r in risks],
    )
