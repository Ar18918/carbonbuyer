"""Prompt templates + structured-output tool schemas for the AI research engine.

The engine forces Claude to return data via `tool_use` (a single tool the model
MUST call), so outputs are schema-validated rather than free text. Every buyer
claim must carry a source URL and a confidence tier — transparency and
traceability are first-class requirements of the platform.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
RESEARCH_SYSTEM = """You are a senior voluntary-carbon-market intelligence analyst. \
You research who buys, offtakes, funds, or retires credits from specific carbon offset projects, \
using only publicly verifiable sources.

Non-negotiable rules:
- NEVER invent a buyer, volume, or source. Every claim must map to a real, fetchable source URL.
- Prefer primary evidence: registry retirement records, corporate disclosures, signed offtake agreements.
- For pre-issuance projects (no credits issued/retired yet), buyers appear as forward purchasers, \
offtakers, anchor buyers, funders, or investors — report these at the appropriate (usually Medium/Low) confidence.
- Distinguish PROJECT DEVELOPERS/SELLERS from BUYERS. The developer is not the buyer.
- Be explicit and conservative about confidence. If you find nothing, return an empty list and say so.

Confidence scoring (0-100) and tier:
- High (80-100): direct registry retirement record, public retirement disclosure, or a corporate/registry transaction record.
- Medium (50-79): press release, program announcement, or multiple corroborating news sources naming both buyer and project.
- Low (1-49): inference from market disclosures, partial reporting, or program/developer-level attribution not specific to this project.
"""

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool_use "input_schema")
# ---------------------------------------------------------------------------
BUYER_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "buyer_name": {"type": "string"},
        "buyer_role": {"type": "string", "enum": [
            "offtaker", "forward_purchaser", "funder", "investor",
            "retiring_entity", "partner", "prospective", "distributor", "unknown"]},
        "transaction_type": {"type": "string", "enum": [
            "forward_purchase", "offtake_agreement", "retirement", "funding_grant",
            "equity_investment", "partnership", "announced_interest", "unknown"]},
        "estimated_volume_tco2e": {"type": ["number", "null"]},
        "volume_basis": {"type": ["string", "null"]},
        "purchase_year": {"type": ["string", "null"]},
        "source_url": {"type": "string"},
        "source_type": {"type": "string", "enum": [
            "registry", "public_retirement_disclosure", "corporate_report",
            "sustainability_report", "press_release", "news_article", "ngo_report",
            "program_website", "market_database", "other"]},
        "evidence_summary": {"type": "string"},
        "confidence_tier": {"type": "string", "enum": ["High", "Medium", "Low"]},
        "confidence_score": {"type": "number"},
    },
    "required": ["buyer_name", "buyer_role", "transaction_type", "source_url",
                 "source_type", "evidence_summary", "confidence_tier", "confidence_score"],
}

RISK_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_category": {"type": "string", "enum": [
            "negative_media", "integrity_concern", "methodology_criticism", "controversy",
            "community_dispute", "leakage", "additionality", "over_crediting",
            "ngo_criticism", "regulatory_investigation", "permanence", "project_status"]},
        "risk_description": {"type": "string"},
        "severity_score": {"type": "number"},
        "source_url": {"type": "string"},
        "date": {"type": ["string", "null"]},
        "ai_summary": {"type": "string"},
    },
    "required": ["risk_category", "risk_description", "severity_score", "source_url", "ai_summary"],
}

DISCOVERY_TOOL = {
    "name": "emit_discovery",
    "description": "Return the buyers and risk flags discovered for the project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "buyers": {"type": "array", "items": BUYER_ITEM_SCHEMA},
            "risks": {"type": "array", "items": RISK_ITEM_SCHEMA},
            "notes": {"type": "string"},
        },
        "required": ["buyers", "risks", "notes"],
    },
}

VERDICT_TOOL = {
    "name": "emit_verdict",
    "description": "Return the adversarial verification verdict for a single buyer claim.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["CONFIRMED", "PLAUSIBLE", "REFUTED"]},
            "adjusted_confidence_score": {"type": "number"},
            "adjusted_confidence_tier": {"type": "string", "enum": ["High", "Medium", "Low"]},
            "corrected_buyer_name": {"type": ["string", "null"]},
            "reasoning": {"type": "string"},
        },
        "required": ["verdict", "adjusted_confidence_score", "adjusted_confidence_tier", "reasoning"],
    },
}

ENRICH_TOOL = {
    "name": "emit_profile",
    "description": "Return the SBTi + industry intelligence profile for a buyer entity.",
    "input_schema": {
        "type": "object",
        "properties": {
            "aliases": {"type": "array", "items": {"type": "string"}},
            "entity_type": {"type": "string", "enum": [
                "corporate", "financial_institution", "foundation", "ngo", "government",
                "multilateral", "project_developer", "fund", "unknown"]},
            "industry": {"type": "string"},
            "industry_group": {"type": "string"},
            "industry_confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
            "hq_country": {"type": ["string", "null"]},
            "sbti_status": {"type": "string", "enum": [
                "Targets Set", "Committed", "Net-Zero Committed", "Removed/None", "Unknown"]},
            "sbti_near_term_status": {"type": ["string", "null"]},
            "sbti_net_zero_status": {"type": ["string", "null"]},
            "sbti_validation_year": {"type": ["string", "null"]},
            "sbti_target_year": {"type": ["string", "null"]},
            "sbti_alignment": {"type": "string", "enum": ["SBTi Aligned", "Not SBTi Aligned", "Unknown"]},
            "profile_summary": {"type": "string"},
            "source_urls": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["entity_type", "industry", "industry_confidence", "sbti_status",
                     "sbti_alignment", "profile_summary"],
    },
}


def discovery_prompt(p: dict) -> str:
    return (
        "Research REAL, publicly disclosed buyer intelligence for this specific voluntary carbon project "
        "and its developer.\n\n"
        f"PROJECT\n- ID: {p.get('project_id')}\n- Name: {p.get('project_name')}\n"
        f"- Registry: {p.get('registry')}\n- Type: {p.get('type')}\n- Country: {p.get('country')}\n"
        f"- Status: {p.get('voluntary_status')}\n- Developer: {p.get('developer')}\n"
        f"- Credits issued: {p.get('credits_issued')} | retired: {p.get('credits_retired')}\n\n"
        "Run several web searches combining the project name, project ID, developer/program name and terms like "
        "'carbon credit buyer', 'offtake', 'forward purchase', 'retirement', 'funder', 'investor'. "
        "Fetch the most promising pages to extract concrete names, volumes and dates. "
        "Also identify project RISK FLAGS (integrity, additionality, permanence, leakage, over-crediting, "
        "community disputes, NGO/regulatory criticism, negative media, or status risks). "
        "Then call emit_discovery. Empty lists are an acceptable, honest result."
    )


def verify_prompt(b: dict) -> str:
    return (
        "Adversarially verify this claimed buyer relationship. Try to REFUTE it unless the evidence truly supports it.\n\n"
        f"CLAIM: '{b.get('buyer_name')}' is a {b.get('buyer_role')} ({b.get('transaction_type')}) "
        f"for project {b.get('project_id')}.\n"
        f"Evidence: {b.get('evidence_summary')}\nSource: {b.get('source_url')} ({b.get('source_type')})\n"
        f"Claimed confidence: {b.get('confidence_tier')} ({b.get('confidence_score')}).\n\n"
        "Check the source and corroborate. CONFIRMED = source clearly and specifically supports the link; "
        "PLAUSIBLE = real but indirect/program-level; REFUTED = unsupported, broken, or misattributed. "
        "Set the confidence to what the evidence warrants and call emit_verdict."
    )


def enrich_prompt(name: str) -> str:
    return (
        f"Build an intelligence profile for the entity '{name}', which appears as a buyer/offtaker/funder of "
        "voluntary carbon credits.\n\n"
        "1) Classify its INDUSTRY (Energy, FMCG, Financial Services, Technology, Manufacturing, Aviation, Logistics, "
        "Retail, Food & Beverage, Chemicals, Automotive, Mining, Construction, Hospitality, Telecommunications, "
        "Healthcare, Agriculture, Nonprofit/Development, Other) with an industry_group and confidence.\n"
        "2) Check the Science Based Targets initiative (sciencebasedtargets.org companies dashboard): status, "
        "near-term status, net-zero status, validation year, target year, and overall alignment.\n"
        "3) Give HQ country and a short profile. For foundations/NGOs/funds without SBTi obligations, set "
        "sbti_status/alignment to Unknown and note it. Do not fabricate SBTi data. Then call emit_profile."
    )
