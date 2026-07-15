"""The AI research engine.

Orchestrates buyer discovery -> adversarial verification -> SBTi/industry
enrichment -> risk assessment for a segment of projects, using the Claude API
with server-side web search and forced structured tool output.

The same four-stage methodology is mirrored by the offline research workflow
that produced the shipped Malawi A/R seed snapshot.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.constants import tier_from_score
from app.db.models import Buyer, BuyerProjectLink, Project, ResearchRun, RiskFlag
from app.research import prompts
from app.research.web_search import anthropic_web_search_tool
from app.services import aggregation, filters as filter_svc
from app.schemas import ProjectFilters, ResearchRequest
from app.util import normalize_name

log = logging.getLogger("research.engine")

try:  # optional dependency — engine degrades gracefully without it
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


def _extract_json(text: str) -> dict | None:
    """Extract the first balanced JSON object from an LLM reply (handles code fences,
    surrounding prose and nested objects/arrays via string-aware brace matching)."""
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class ResearchEngine:
    """Two auth modes:

    * api_key      — Anthropic Messages API with x-api-key (server-side web search + forced tool output)
    * subscription — Claude Agent SDK authenticated by CLAUDE_CODE_OAUTH_TOKEN (rides on a Claude
                     Max/Pro plan; no API key, no per-token billing). Uses the Claude Code CLI + its
                     WebSearch/WebFetch tools, and returns schema-conforming JSON parsed from the reply.
    """

    def __init__(self) -> None:
        self.model = settings.research_model
        self.api_key = settings.anthropic_api_key
        self.oauth_token = settings.claude_code_oauth_token
        pref = (settings.research_auth_mode or "auto").lower()
        self.mode = "none"
        self.client = None
        if pref in ("auto", "api_key") and self.api_key and anthropic:
            self.mode = "api_key"
            self.client = anthropic.Anthropic(api_key=self.api_key)
        elif pref in ("auto", "subscription") and self.oauth_token:
            self.mode = "subscription"
        self.enabled = self.mode != "none"

    # Map friendly aliases -> full API model IDs. The Claude Code CLI (subscription) also accepts aliases.
    _API_MODEL_IDS = {
        "opus": "claude-opus-4-8", "sonnet": "claude-sonnet-5", "haiku": "claude-haiku-4-5-20251001",
    }

    def _resolve_model(self, requested: str | None) -> str:
        m = requested or self.model
        if self.mode == "api_key":
            return self._API_MODEL_IDS.get(m, m)
        return m  # Claude Code CLI accepts aliases and full IDs as-is

    # ------------------------------------------------------------------ core
    def _emit(self, prompt: str, tool: dict, use_web: bool, model: str, max_turns: int) -> dict | None:
        if not self.enabled:
            raise RuntimeError("Research engine disabled: set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN.")
        if self.mode == "subscription":
            return self._emit_subscription(prompt, tool, use_web, model, max_turns)
        return self._emit_api(prompt, tool, use_web, model)

    # --- subscription mode (Claude Agent SDK + OAuth token) ---
    # Fail fast on the subscription path: a rate-limited CLI won't recover on retry, and retrying
    # only burns more of the user's subscription quota.
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
    def _emit_subscription(self, prompt: str, tool: dict, use_web: bool, model: str, max_turns: int) -> dict | None:
        schema = json.dumps(tool["input_schema"])
        system = (
            prompts.RESEARCH_SYSTEM
            + "\n\nOUTPUT FORMAT: After researching, reply with a SINGLE JSON object that conforms to this "
            f"JSON Schema and NOTHING else — no prose, no markdown fences:\n{schema}"
        )
        full = prompt + "\n\nWhen finished, output ONLY the JSON object described in the system prompt."
        text = asyncio.run(self._agent_query(full, system, use_web, model, max_turns))
        return _extract_json(text)

    async def _agent_query(self, prompt: str, system: str, allow_web: bool, model: str, max_turns: int) -> str:
        from claude_agent_sdk import ClaudeAgentOptions, query  # lazy import (CLI-backed)

        options = ClaudeAgentOptions(
            system_prompt=system,
            # Pre-authorize the read-only web tools via the allowlist. permission_mode stays "default"
            # because "bypassPermissions" maps to --dangerously-skip-permissions, which Claude Code
            # refuses to run as root (the backend container runs as root).
            allowed_tools=(["WebSearch", "WebFetch"] if allow_web else []),
            permission_mode="default",
            max_turns=max_turns,
            model=model,
        )
        parts: list[str] = []
        result_text: str | None = None
        # Hard timeout so a hung CLI subprocess can never stall the whole run (the 57-min hang).
        async with asyncio.timeout(settings.research_call_timeout):
            async for message in query(prompt=prompt, options=options):
                if type(message).__name__ == "ResultMessage":
                    r = getattr(message, "result", None)
                    if isinstance(r, str):
                        result_text = r
                content = getattr(message, "content", None)
                if isinstance(content, list):
                    for block in content:
                        txt = getattr(block, "text", None)
                        if isinstance(txt, str):
                            parts.append(txt)
                elif isinstance(content, str):
                    parts.append(content)
        # ResultMessage.result is the clean final answer; fall back to concatenated assistant text.
        return result_text or "\n".join(parts)

    # --- api-key mode (Anthropic Messages API) ---
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
    def _emit_api(self, prompt: str, tool: dict, use_web: bool, model: str) -> dict | None:
        """Run one Messages call and return the input of the forced emit tool."""
        tools = [tool]
        extra = {}
        if use_web and settings.web_search_provider == "anthropic":
            tools = [anthropic_web_search_tool(), tool]

        messages = [{"role": "user", "content": prompt}]
        # Round 1: allow the model to search, then (ideally) call the emit tool.
        resp = self.client.messages.create(
            model=model,
            max_tokens=settings.research_max_tokens,
            system=prompts.RESEARCH_SYSTEM,
            tools=tools,
            tool_choice={"type": "auto"},
            messages=messages,
            **extra,
        )
        found = self._extract_tool(resp, tool["name"])
        if found is not None:
            return found

        # Round 2: force the emit tool (no web search) so we always get structured output.
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": f"Now call {tool['name']} with your findings."})
        resp2 = self.client.messages.create(
            model=model,
            max_tokens=settings.research_max_tokens,
            system=prompts.RESEARCH_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=messages,
        )
        return self._extract_tool(resp2, tool["name"])

    @staticmethod
    def _extract_tool(resp, name: str) -> dict | None:
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == name:
                return dict(block.input)
        return None

    # ------------------------------------------------------------- stages
    def discover(self, project: dict, model: str, max_turns: int) -> dict:
        out = self._emit(prompts.discovery_prompt(project), prompts.DISCOVERY_TOOL, True, model, max_turns)
        return out or {"buyers": [], "risks": [], "notes": "no output"}

    def verify(self, buyer: dict, model: str, max_turns: int) -> dict:
        out = self._emit(prompts.verify_prompt(buyer), prompts.VERDICT_TOOL, True, model, max_turns)
        return out or {"verdict": "PLAUSIBLE", "adjusted_confidence_score": buyer.get("confidence_score", 30),
                       "adjusted_confidence_tier": buyer.get("confidence_tier", "Low"),
                       "reasoning": "verification unavailable"}

    def enrich(self, name: str, model: str, max_turns: int) -> dict:
        out = self._emit(prompts.enrich_prompt(name), prompts.ENRICH_TOOL, True, model, max_turns)
        return out or {"entity_type": "unknown", "industry": "Other", "industry_confidence": "Low",
                       "sbti_status": "Unknown", "sbti_alignment": "Unknown", "profile_summary": ""}

    # ------------------------------------------------------------- persistence
    def _upsert_buyer(self, db: Session, name: str, run_id: int | None, model: str, max_turns: int) -> Buyer:
        key = normalize_name(name)
        buyer = db.query(Buyer).filter(Buyer.normalized_name == key).one_or_none()
        if buyer:
            return buyer
        profile = {}
        try:
            profile = self.enrich(name, model, max_turns)
        except Exception as exc:  # pragma: no cover
            log.warning("enrich failed for %s: %s", name, exc)
        buyer = Buyer(
            name=name,
            normalized_name=key,
            aliases=profile.get("aliases", []),
            entity_type=profile.get("entity_type", "unknown"),
            industry=profile.get("industry", "Other"),
            industry_group=profile.get("industry_group", ""),
            industry_confidence=profile.get("industry_confidence", "Low"),
            hq_country=profile.get("hq_country"),
            sbti_status=profile.get("sbti_status", "Unknown"),
            sbti_near_term_status=profile.get("sbti_near_term_status"),
            sbti_net_zero_status=profile.get("sbti_net_zero_status"),
            sbti_validation_year=profile.get("sbti_validation_year"),
            sbti_target_year=profile.get("sbti_target_year"),
            sbti_alignment=profile.get("sbti_alignment", "Unknown"),
            profile_summary=profile.get("profile_summary", ""),
            source_urls=profile.get("source_urls", []),
        )
        db.add(buyer)
        db.flush()
        return buyer

    def research_segment(self, db: Session, req: ResearchRequest, run: ResearchRun | None = None) -> ResearchRun:
        # Use the caller's filter as-is (supports multi-country); only synthesize one when absent.
        filt = req.filters or ProjectFilters(country=req.country, project_type=req.project_type)

        model = self._resolve_model(req.model)
        max_turns = req.max_turns
        do_verify = req.verify

        # Reuse the caller's run record (so a polling client sees this exact run progress),
        # or create one when invoked directly.
        if run is None:
            run = ResearchRun(country=req.country, project_type=req.project_type,
                              params=filt.model_dump(), status="running", model=model)
            db.add(run)
        else:
            run.status = "running"
            run.model = model
        db.commit()
        db.refresh(run)

        try:
            projects = filter_svc.query_projects(db, filt).limit(req.max_projects).all()
            buyers_found = 0
            disc_failures = 0
            last_err = None
            for proj in projects:
                pdata = {c: getattr(proj, c) for c in (
                    "project_id", "project_name", "registry", "type", "country",
                    "voluntary_status", "developer", "credits_issued", "credits_retired")}
                try:
                    disc = self.discover(pdata, model, max_turns)
                except Exception as exc:
                    disc_failures += 1
                    last_err = str(exc)
                    log.warning("discovery failed for %s: %s", proj.project_id, exc)
                    continue

                # risks
                for r in disc.get("risks", []):
                    db.add(RiskFlag(
                        project_id=proj.id, risk_category=r.get("risk_category", ""),
                        risk_description=r.get("risk_description", ""),
                        severity_score=float(r.get("severity_score", 0) or 0),
                        source_url=r.get("source_url", ""), date=r.get("date"),
                        ai_summary=r.get("ai_summary", ""), research_run_id=run.id))

                # buyers -> verify -> persist
                for b in disc.get("buyers", []):
                    b["project_id"] = proj.project_id
                    fallback = {"verdict": "PLAUSIBLE",
                                "adjusted_confidence_score": b.get("confidence_score", 30),
                                "adjusted_confidence_tier": b.get("confidence_tier", "Low")}
                    if do_verify:
                        try:
                            v = self.verify(b, model, max_turns)
                        except Exception:
                            v = fallback
                    else:
                        v = fallback  # intensity=light skips the verification stage
                    if v.get("verdict") == "REFUTED":
                        continue
                    name = v.get("corrected_buyer_name") or b.get("buyer_name")
                    if not name:
                        continue
                    score = float(v.get("adjusted_confidence_score", b.get("confidence_score", 0)) or 0)
                    buyer = self._upsert_buyer(db, name, run.id, model, max_turns)
                    db.add(BuyerProjectLink(
                        buyer_id=buyer.id, project_id=proj.id,
                        buyer_role=b.get("buyer_role", "unknown"),
                        transaction_type=b.get("transaction_type", "unknown"),
                        estimated_volume_tco2e=b.get("estimated_volume_tco2e"),
                        retirement_volume_tco2e=(b.get("estimated_volume_tco2e")
                                                 if b.get("transaction_type") == "retirement" else None),
                        volume_basis=b.get("volume_basis"),
                        purchase_year=b.get("purchase_year"),
                        source_url=b.get("source_url", ""),
                        source_type=b.get("source_type", "other"),
                        evidence_summary=b.get("evidence_summary", ""),
                        confidence_tier=v.get("adjusted_confidence_tier") or tier_from_score(score),
                        confidence_score=score,
                        verdict=v.get("verdict"),
                        research_run_id=run.id))
                    buyers_found += 1
                db.commit()

            aggregation.recompute_all(db)
            run.projects_researched = len(projects)
            run.buyers_found = buyers_found
            run.completed_at = datetime.now(timezone.utc)
            if buyers_found == 0 and disc_failures:
                run.status = "failed"
                run.error = (
                    "Research calls failed — most likely the Claude subscription rate limit. "
                    "Retry after your limit resets, pick a lighter model/intensity, or set ANTHROPIC_API_KEY. "
                    f"(last error: {(last_err or '')[:160]})")
            else:
                run.status = "completed"
        except Exception as exc:  # pragma: no cover
            log.exception("research run failed")
            run.status = "failed"
            run.error = str(exc)
        db.commit()
        db.refresh(run)
        return run


engine = ResearchEngine()
