"""Pydantic request/response schemas (API contract)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectFilters(BaseModel):
    """The core search request. Country + project type are the primary axes."""
    country: str | None = None
    countries: list[str] | None = None   # multi-select; takes precedence over `country`
    project_type: str | None = None
    registry: str | None = None
    region: str | None = None
    reduction_removal: str | None = None
    vintage_year_min: int | None = None
    vintage_year_max: int | None = None
    credits_issued_min: float | None = None
    credits_issued_max: float | None = None
    credits_retired_min: float | None = None
    credits_retired_max: float | None = None
    include_ineligible: bool = False  # if True, bypass status/vintage exclusion rules
    search: str | None = None         # free-text on project name / id / developer


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: str
    project_name: str
    registry: str
    voluntary_status: str
    scope: str
    type: str
    reduction_removal: str
    methodology: str
    region: str
    country: str
    state: str
    developer: str
    credits_issued: float
    credits_retired: float
    credits_remaining: float
    first_vintage_year: int | None
    is_eligible: bool
    risk_count: int = 0
    buyer_count: int = 0


class BuyerLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    buyer_id: int
    project_id: int
    buyer_role: str
    transaction_type: str
    estimated_volume_tco2e: float | None
    retirement_volume_tco2e: float | None
    purchase_year: str | None
    source_url: str
    source_type: str
    evidence_summary: str
    confidence_tier: str
    confidence_score: float
    verdict: str | None


class BuyerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    entity_type: str
    industry: str
    industry_group: str
    industry_confidence: str
    hq_country: str | None
    sbti_status: str
    sbti_alignment: str
    sbti_validation_year: str | None
    sbti_target_year: str | None
    profile_summary: str
    source_urls: list[str]
    total_estimated_volume: float
    total_retired_volume: float
    total_non_retired_volume: float
    num_projects: int
    num_countries: int
    num_project_types: int
    num_purchase_years: int
    repeat_purchase_count: int
    total_repeat_volume: float
    repeat_buyer_score: float
    is_repeat_buyer: bool


class RiskFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    risk_category: str
    risk_description: str
    severity_score: float
    source_url: str
    date: str | None
    ai_summary: str


class KPIs(BaseModel):
    total_buyers: int
    total_estimated_volume: float
    total_projects: int
    repeat_buyer_pct: float
    sbti_aligned_pct: float


class NameValue(BaseModel):
    name: str
    value: float


class NameValue2(BaseModel):
    name: str
    value: float
    value2: float = 0.0


class DashboardResponse(BaseModel):
    filters: ProjectFilters
    kpis: KPIs
    buyer_count: int
    top_buyers: list[BuyerOut]
    repeat_buyers: list[BuyerOut]
    buyer_frequency: list[NameValue]          # one-time vs repeat
    vintage_activity: list[NameValue]         # volume by vintage year
    retirement_activity: list[NameValue]      # retirement volume by year
    retirement_split: list[NameValue]         # retired vs non-retired
    volume_by_region: list[NameValue]
    volume_by_country: list[NameValue]
    volume_by_reduction_removal: list[NameValue]
    volume_by_registry: list[NameValue]
    sbti_alignment: list[NameValue]
    industry_segmentation: list[NameValue2]   # buyer count + volume share per industry
    projects: list[ProjectOut]
    risks: list[RiskFlagOut]


# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str = ""
    role: str = "analyst"


class SavedSearchIn(BaseModel):
    name: str
    params: ProjectFilters


class SavedSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    params: dict


class ResearchRequest(BaseModel):
    country: str
    project_type: str
    filters: ProjectFilters | None = None
    max_projects: int = 25
    model: str | None = None      # "opus" | "sonnet" | "haiku" | full id | None (engine default)
    verify: bool = True           # run the adversarial verification stage
    max_turns: int = 10           # per-agent tool turns (subscription mode)


class ResearchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    country: str | None
    project_type: str | None
    status: str
    model: str
    projects_researched: int
    buyers_found: int
    error: str | None
