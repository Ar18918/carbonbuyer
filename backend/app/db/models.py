"""SQLAlchemy ORM models — the platform data layer.

Entities
--------
Project              one row per offset project (from the Excel PROJECTS tab)
Buyer                a distinct buyer/offtaker/funder entity (aggregated)
BuyerProjectLink     project -> buyer evidence record (the research output)
RiskFlag             project red-flag / integrity concern
ResearchRun          an execution of the AI research engine for a segment
User / SavedSearch   RBAC + saved searches
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(Text, default="")
    registry: Mapped[str] = mapped_column(String(16), index=True, default="")
    arb_wa_project: Mapped[str] = mapped_column(String(16), default="")
    voluntary_status: Mapped[str] = mapped_column(String(256), index=True, default="")
    scope: Mapped[str] = mapped_column(String(256), default="")
    type: Mapped[str] = mapped_column(String(256), index=True, default="")
    reduction_removal: Mapped[str] = mapped_column(String(64), index=True, default="")
    methodology: Mapped[str] = mapped_column(Text, default="")
    methodology_version: Mapped[str] = mapped_column(Text, default="")
    region: Mapped[str] = mapped_column(String(128), index=True, default="")
    country: Mapped[str] = mapped_column(String(128), index=True, default="")
    state: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(Text, default="")
    developer: Mapped[str] = mapped_column(Text, default="")

    credits_issued: Mapped[float] = mapped_column(Float, default=0.0)
    credits_retired: Mapped[float] = mapped_column(Float, default=0.0)
    credits_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    buffer_deposits: Mapped[float] = mapped_column(Float, default=0.0)
    reversals_covered: Mapped[float] = mapped_column(Float, default=0.0)
    reversals_not_covered: Mapped[float] = mapped_column(Float, default=0.0)
    buffer_released: Mapped[float] = mapped_column(Float, default=0.0)
    first_vintage_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # per-vintage-year issuance {year: credits}; populated by the ETL from the wide columns
    vintage_issuance: Mapped[dict] = mapped_column(JSON, default=dict)

    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    links: Mapped[list["BuyerProjectLink"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    risks: Mapped[list["RiskFlag"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    normalized_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    entity_type: Mapped[str] = mapped_column(String(64), default="unknown")

    # Industry segmentation
    industry: Mapped[str] = mapped_column(String(64), default="Other", index=True)
    industry_group: Mapped[str] = mapped_column(String(96), default="")
    industry_confidence: Mapped[str] = mapped_column(String(16), default="Low")
    hq_country: Mapped[str | None] = mapped_column(String(96), nullable=True)

    # SBTi intelligence
    sbti_status: Mapped[str] = mapped_column(String(64), default="Unknown")
    sbti_near_term_status: Mapped[str | None] = mapped_column(String(96), nullable=True)
    sbti_net_zero_status: Mapped[str | None] = mapped_column(String(96), nullable=True)
    sbti_validation_year: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sbti_target_year: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sbti_alignment: Mapped[str] = mapped_column(String(32), default="Unknown", index=True)

    profile_summary: Mapped[str] = mapped_column(Text, default="")
    source_urls: Mapped[list] = mapped_column(JSON, default=list)

    # --- Aggregates (recomputed by the aggregation service) ---
    total_estimated_volume: Mapped[float] = mapped_column(Float, default=0.0)
    total_retired_volume: Mapped[float] = mapped_column(Float, default=0.0)
    total_non_retired_volume: Mapped[float] = mapped_column(Float, default=0.0)
    num_projects: Mapped[int] = mapped_column(Integer, default=0)
    num_countries: Mapped[int] = mapped_column(Integer, default=0)
    num_project_types: Mapped[int] = mapped_column(Integer, default=0)
    num_purchase_years: Mapped[int] = mapped_column(Integer, default=0)
    repeat_purchase_count: Mapped[int] = mapped_column(Integer, default=0)
    total_repeat_volume: Mapped[float] = mapped_column(Float, default=0.0)
    repeat_buyer_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_repeat_buyer: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    links: Mapped[list["BuyerProjectLink"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")


class BuyerProjectLink(Base):
    """A single piece of buyer evidence tying a buyer to a project (research output)."""
    __tablename__ = "buyer_project_links"
    __table_args__ = (UniqueConstraint("buyer_id", "project_id", "source_url", name="uq_link_evidence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)

    buyer_role: Mapped[str] = mapped_column(String(48), default="unknown")
    transaction_type: Mapped[str] = mapped_column(String(48), default="unknown")
    estimated_volume_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    retirement_volume_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_year: Mapped[str | None] = mapped_column(String(16), nullable=True)

    source_url: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(48), default="other")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    confidence_tier: Mapped[str] = mapped_column(String(16), default="Low", index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)  # CONFIRMED / PLAUSIBLE

    research_run_id: Mapped[int | None] = mapped_column(ForeignKey("research_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    buyer: Mapped["Buyer"] = relationship(back_populates="links")
    project: Mapped["Project"] = relationship(back_populates="links")


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    risk_category: Mapped[str] = mapped_column(String(48), index=True, default="")
    risk_description: Mapped[str] = mapped_column(Text, default="")
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_url: Mapped[str] = mapped_column(Text, default="")
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    research_run_id: Mapped[int | None] = mapped_column(ForeignKey("research_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    project: Mapped["Project"] = relationship(back_populates="risks")


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str | None] = mapped_column(String(96), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending/running/completed/failed
    model: Mapped[str] = mapped_column(String(64), default="")
    projects_researched: Mapped[int] = mapped_column(Integer, default=0)
    buyers_found: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(24), default="analyst")  # admin / analyst / viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    saved_searches: Mapped[list["SavedSearch"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="saved_searches")
