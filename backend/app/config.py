"""Application configuration loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_name: str = "Carbon Credit Buyer Intelligence Platform"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    # e.g. postgresql+psycopg://postgres:postgres@db:5432/carbon
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/carbon"

    # --- Auth / RBAC ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    # First user created with this email becomes an admin.
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "changeme"

    # --- AI research layer ---
    # Auth: "api_key" uses ANTHROPIC_API_KEY; "subscription" uses a Claude Max/Pro OAuth token
    # (CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`) via the Claude Agent SDK — no API key/billing.
    # "auto" prefers an API key if present, else falls back to the subscription token.
    research_auth_mode: str = "auto"
    anthropic_api_key: str | None = None
    claude_code_oauth_token: str | None = None
    research_model: str = "claude-opus-4-8"
    research_max_tokens: int = 4096
    # Hard ceiling per single agent/model call (seconds) so a hung subprocess can't stall a run.
    research_call_timeout: int = 180
    # Web search provider for the research engine. Supported: "anthropic" (native tool), "tavily", "serper", "none"
    web_search_provider: str = "anthropic"
    tavily_api_key: str | None = None
    serper_api_key: str | None = None
    research_concurrency: int = 4
    # Max projects the on-demand "Analyze market" flow researches per run (keeps latency/cost bounded).
    research_auto_max_projects: int = 15
    # Require an analyst login to trigger the /research/analyze on-demand flow. Off by default so the
    # "Analyze market" button works out of the box; turn on to gate live research behind RBAC.
    research_requires_auth: bool = False

    # --- ETL ---
    # Path to the master Excel workbook (mounted into the container by docker-compose).
    excel_path: str = "/data/Voluntary-Registry-Offsets-Database.xlsx"
    projects_sheet: str = "PROJECTS"
    # Pre-extracted seed CSV shipped in the repo so the DB can be seeded without opening the 16MB workbook.
    seed_csv_path: str = "/data/seed/projects.csv"
    seed_research_path: str = "/data/seed/malawi_ar_research.json"
    # All pre-seeded market snapshots (Malawi, India, …) are loaded from this glob.
    seed_research_glob: str = "/data/seed/*_research.json"
    # Pre-matched registry retirements (OffsetsDB harmonized beneficiaries, joined to our project_ids)
    # that power the deterministic "Registered buyers" path — no AI, no tokens.
    seed_registry_csv: str = "/data/seed/offsetsdb_retirements.csv"
    # Deterministic industry + SBTi enrichment for registered buyers (SBTi dataset + curated map).
    seed_buyer_enrichment_csv: str = "/data/seed/buyer_enrichment.csv"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
