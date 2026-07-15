"""Domain constants and the deterministic project-eligibility rules.

These encode the filtering logic from the platform spec, calibrated against the
*actual* value set observed in Voluntary Registry Offsets Database v2026-04.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Project eligibility
# ---------------------------------------------------------------------------
# A project is EXCLUDED if its (normalised) Voluntary Status contains any of
# these keywords. This captures the spec's exclusion list
# (Withdrawn / Canceled / Cancelled / Validation Unsuccessful / Inactive /
# Verification Request Denied) plus the real-world variants present in the
# database, e.g. "validation_unsuccessful", "Rejected by Administrator",
# "Registration request denied", "Verification approval request denied".
EXCLUDED_STATUS_KEYWORDS = (
    "withdrawn",
    "cancel",          # canceled / cancelled
    "inactive",
    "unsuccessful",    # validation unsuccessful / validation_unsuccessful
    "denied",          # *request denied variants
    "rejected",        # rejected by administrator
)

# Minimum vintage year (inclusive). Projects with a *known* first vintage year
# earlier than this are excluded. Pre-issuance projects (no vintage yet) are
# retained — they are exactly where forward-purchase buyer intelligence lives.
MIN_VINTAGE_YEAR = 2015


def normalise_status(status: str | None) -> str:
    return (status or "").strip().lower().replace("_", " ")


def is_status_excluded(status: str | None) -> bool:
    s = normalise_status(status)
    if not s:
        return False
    return any(kw in s for kw in EXCLUDED_STATUS_KEYWORDS)


def is_vintage_eligible(first_vintage_year: int | None) -> bool:
    if first_vintage_year is None:
        return True  # pre-issuance / unknown vintage is retained
    return first_vintage_year >= MIN_VINTAGE_YEAR


def is_project_eligible(status: str | None, first_vintage_year: int | None) -> bool:
    return (not is_status_excluded(status)) and is_vintage_eligible(first_vintage_year)


# ---------------------------------------------------------------------------
# Registries (as they appear in the database)
# ---------------------------------------------------------------------------
REGISTRIES = ["VCS", "GOLD", "CAR", "ACR", "ISO", "ART"]
REGISTRY_LABELS = {
    "VCS": "Verra (VCS)",
    "GOLD": "Gold Standard",
    "CAR": "Climate Action Reserve",
    "ACR": "American Carbon Registry",
    "ISO": "Isometric",
    "ART": "Architecture for REDD+ Transactions",
}

REDUCTION_REMOVAL_VALUES = ["Reduction", "Mixed", "Impermanent Removal", "Long-Duration Removal"]

# ---------------------------------------------------------------------------
# Industry taxonomy for buyer segmentation
# ---------------------------------------------------------------------------
INDUSTRIES = [
    "Energy", "FMCG", "Financial Services", "Technology", "Manufacturing",
    "Aviation", "Logistics", "Retail", "Food & Beverage", "Chemicals",
    "Automotive", "Mining", "Construction", "Hospitality", "Telecommunications",
    "Healthcare", "Agriculture", "Nonprofit/Development", "Other",
]

CONFIDENCE_TIERS = ["High", "Medium", "Low"]

SBTI_ALIGNMENT = ["SBTi Aligned", "Not SBTi Aligned", "Unknown"]


def tier_from_score(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


# Human-readable labels for the AI research engine's risk-category slugs.
RISK_CATEGORY_LABELS = {
    "project_status": "Delivery / project status",
    "delivery": "Delivery risk",
    "permanence": "Permanence / reversal",
    "reversal": "Permanence / reversal",
    "over_crediting": "Over-crediting",
    "additionality": "Additionality",
    "leakage": "Leakage",
    "integrity_concern": "Integrity concern",
    "controversy": "Controversy",
    "governance": "Governance",
    "financial": "Financial / counterparty",
    "counterparty": "Counterparty",
    "methodology": "Methodology",
    "measurement": "Measurement / MRV",
    "mrv": "Measurement / MRV",
    "social": "Social / community",
    "community": "Social / community",
}


def humanize_risk(category: str | None) -> str:
    """Turn a risk-category slug (e.g. 'over_crediting') into a readable label."""
    if not category:
        return "Unspecified"
    key = category.strip().lower()
    if key in RISK_CATEGORY_LABELS:
        return RISK_CATEGORY_LABELS[key]
    return key.replace("_", " ").replace("-", " ").strip().capitalize()


_YEAR_RE = re.compile(r"(19|20)\d{2}")


def parse_year(value) -> int | None:
    """Best-effort extraction of a 4-digit year from a cell that may be a float, int or string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            y = int(value)
            return y if 1900 <= y <= 2100 else None
        except (ValueError, OverflowError):
            return None
    m = _YEAR_RE.search(str(value))
    return int(m.group(0)) if m else None
