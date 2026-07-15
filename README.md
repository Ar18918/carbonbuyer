# Carbon Credit Buyer Intelligence Platform

An enterprise platform that lets analysts search carbon offset projects by geography and
type, **identify likely buyers** using an AI research engine, estimate purchase volumes,
enrich buyer profiles (industry + SBTi), flag project integrity risks, and generate market
intelligence dashboards and downloadable datasets.

Built on the **Berkeley Carbon Trading Project — Voluntary Registry Offsets Database
v2026-04** (11,343 projects across Verra/VCS, Gold Standard, CAR, ACR, Isometric and ART).

- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind · shadcn-style UI · Recharts
- **Backend:** Python · FastAPI · SQLAlchemy 2.0
- **Data:** PostgreSQL · Excel ETL ingestion pipeline
- **AI:** Claude API (Anthropic) research engine with server-side web search + adversarial verification
- **Auth:** JWT + role-based access control (admin / analyst / viewer), saved searches

---

## ⚠️ Read this first — the data reality that shapes the design

The master database records projects, developers, issuance/retirement **totals** and
per-vintage issuance — **but it does not contain buyer identities.** There is no column for
"who bought or retired these credits."

Therefore the buyer layer is **researched, not extracted.** The AI research engine mines
registry retirement records, public retirement disclosures, corporate/ESG reports, press
releases, NGO reporting and market databases, and records **every buyer claim with a source
URL and a 0–100 confidence score**. Transparency, traceability and confidence scoring are
first-class — nothing is fabricated.

The shipped flagship segment (**Malawi · Afforestation/Reforestation**) is instructive: all
7 projects are **pre-issuance** (0 credits issued/retired), so buyers appear as **forward
purchasers, offtakers, funders and investors** (e.g. Climate Asset Management / HSBC financing
Restore Africa; Trafigura's 40-year Malawi concession) rather than as retirement records — and
the confidence tiers reflect that. This is the honest shape of buyer intelligence for early-stage
African A/R.

---

## Quick start (Docker — one command)

Prerequisites: Docker Desktop.

```bash
cd carbon-buyer-intelligence
cp .env.example .env                # optionally add your ANTHROPIC_API_KEY for live research
docker compose up --build
```

Then open:

- **App:** http://localhost:3000  (opens on a market-selection landing page — pick any country + project type, or click the researched Malawi · A/R example)
- **API docs:** http://localhost:8000/docs
- **Default admin:** `admin@example.com` / `changeme` (change in `.env`)

On first boot the backend automatically:
1. creates the schema,
2. seeds the 11,343 projects from `data/seed/projects.csv`,
3. loads the researched Malawi A/R buyer snapshot from `data/seed/malawi_ar_research.json`,
4. computes buyer aggregates.

> No `ANTHROPIC_API_KEY`? The platform runs fully in **seeded-snapshot mode** — all dashboards,
> filters and exports work against the shipped research snapshot. Add a key to enable **live
> research** on any segment you choose.

### Instant preview (no runtime at all)

Open **`preview.html`** in any browser (double-click). It opens on a market-selection screen: the
researched **Malawi · Afforestation/Reforestation** MVP renders the full dashboard directly from the
embedded snapshot — KPIs, charts, buyer table, risk flags — while other picks point you to the full
platform. Zero install; great for a quick look before spinning up the stack.

---

## Manual / local development

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/carbon
python -m app.seed.seed_db          # create schema + seed projects + research snapshot
uvicorn app.main:app --reload       # http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local    # BACKEND_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
```

---

## The AI research engine

`backend/app/research/` implements the four-stage methodology (the same one used to produce the
shipped snapshot):

| Stage | File | What it does |
|-------|------|--------------|
| **Discovery** | `engine.py` + `prompts.py` | For each shortlisted project, Claude runs server-side web searches and returns structured buyer findings (buyer, role, volume, year, source URL, evidence, confidence) + project risk flags. |
| **Verification** | `engine.py` (`verify`) | Each buyer claim is adversarially re-checked — the model tries to *refute* it. Refuted claims are dropped; confidence is re-scored. |
| **Enrichment** | `engine.py` (`enrich`) | Each unique buyer is profiled for **industry segmentation** and **SBTi** status/alignment. |
| **Aggregation** | `services/aggregation.py` | Roll up per-buyer totals, repeat-buyer detection and scores. |

Structured output is enforced via Claude **tool_use** schemas (`prompts.py`), so results are
validated, not parsed from prose. Web search is pluggable (`web_search.py`): Anthropic native
`web_search`, Tavily, or Serper.

### On-demand "Analyze market" flow (the working model)
Pick a country + project type on the landing page and click **Analyze market**. The dashboard opens
immediately with the deterministic project analytics, then:
1. the frontend calls `POST /api/v1/research/analyze` for the segment;
2. if the segment is already researched it renders instantly; if a run is already in flight it attaches to it;
   otherwise the **AI engine starts in the background** and returns a run id;
3. the page polls the run and **fills in buyers, SBTi and risk when the engine finishes** — showing live
   "N projects researched · N buyers found" progress meanwhile.

This requires `ANTHROPIC_API_KEY` on the backend (otherwise the engine reports "disabled" and the page
shows deterministic analytics only). Research is bounded to `RESEARCH_AUTO_MAX_PROJECTS` (default 15) per
run to keep latency and cost predictable. A **Re-run research** button forces a fresh pass.

### Run live research on a segment (programmatic / RBAC)
```bash
# get a token
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=admin@example.com&password=changeme' | jq -r .access_token
# trigger a run (analyst role+)
curl -X POST http://localhost:8000/api/v1/research/run \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"country":"Kenya","project_type":"Cookstoves","max_projects":15}'
```
The run executes in the background; poll `GET /api/v1/research/runs`.

### About the shipped snapshot
The Malawi · A/R research completed **discovery (all 7 projects), verification, and SBTi + industry
enrichment**. SBTi findings: **HSBC** (exited the SBTi in 2025) and **Mota-Engil** (no validated
targets) are **Not SBTi Aligned**; **Trafigura** and **Rabobank** returned no validated SBTi target
(`Unknown`); the remaining buyers are funds, development banks, NGOs, governments or defunct entities
that carry no corporate SBTi target (`Unknown`/None) — an honest, complete result rather than
fabricated alignment. Industry/entity/HQ classifications are from public sources (high confidence for
well-known entities). Re-run enrichment any time via the research engine on any other segment. See
`data/seed/malawi_ar_research.json → meta.notes`.

---

## Project filtering rules (`backend/app/constants.py`)

Applied before any analysis, calibrated to the real value set in the workbook:

- **Include** projects matching the selected country + project type + optional filters.
- **Exclude** statuses containing: *withdrawn, cancel(l)ed, inactive, (validation) unsuccessful,
  (request) denied, rejected* — covers the spec list plus real variants
  (`validation_unsuccessful`, `Rejected by Administrator`, `Registration request denied`, …).
- **Vintage filter:** exclude projects with a known first vintage year `< 2015`. Pre-issuance
  projects (no vintage yet) are retained — that is where forward-purchase intelligence lives.

The UI exposes an "include ineligible" toggle for auditing.

---

## Dashboards & exports

**KPI cards:** total buyers · est. buyer volume · projects included · repeat-buyer % · SBTi-aligned %.

**13 visualizations:** buyer count · top-20 buyers · top-10 repeat buyers · buyer frequency
(one-time vs repeat) · vintage activity · retirement activity · retirement split · volume by
region / country / reduction-vs-removal / registry · SBTi alignment · industry segmentation.

**Download Centre:** Buyer Intelligence CSV · Project Dataset CSV (with risk flags) ·
Buyer-Project Mapping CSV (with source links + confidence) · Executive Summary (Markdown → print to PDF).

---

## API surface (`/api/v1`)

| Method | Path | Notes |
|-------|------|-------|
| POST | `/auth/login` | OAuth2 password → JWT |
| GET | `/auth/me` | current user |
| POST | `/auth/users` | create user (admin) |
| GET | `/projects/facets` · `/projects/stats` | filter dropdowns + counts |
| POST | `/projects/search` | filtered project list |
| POST | `/analytics/dashboard` | full dashboard payload (KPIs + 13 charts + tables) |
| GET | `/buyers` · `/buyers/{id}` · `/buyers/{id}/links` | buyer intelligence |
| POST | `/research/analyze` | On-demand: start (or reuse) a buyer-research run for a segment; returns a pollable run |
| GET | `/research/status` · POST `/research/run` · GET `/research/runs/{id}` | AI engine status, RBAC trigger, run polling |
| POST | `/exports/{buyers,projects,buyer-project-mapping}.csv` · `/exports/executive-summary.md` | downloads |
| GET/POST/DELETE | `/saved-searches` | per-user saved searches |

---

## Project structure

```
carbon-buyer-intelligence/
├─ docker-compose.yml            # db + backend + frontend
├─ preview.html                  # zero-install flagship dashboard preview
├─ data/seed/
│   ├─ projects.csv              # 11,343 projects (pre-extracted from the workbook)
│   └─ malawi_ar_research.json   # researched buyer/SBTi/risk snapshot
├─ backend/
│   └─ app/
│       ├─ constants.py          # eligibility rules, taxonomy
│       ├─ db/models.py          # Project, Buyer, BuyerProjectLink, RiskFlag, ResearchRun, User…
│       ├─ etl/ingest_excel.py   # Excel + CSV ETL
│       ├─ research/             # engine.py, prompts.py, web_search.py  (the AI layer)
│       ├─ services/             # filters.py, aggregation.py, analytics.py
│       ├─ api/                  # auth, projects, buyers, analytics, research, exports, saved
│       └─ seed/seed_db.py       # bootstrap + seeding
└─ frontend/
    ├─ app/                      # layout, page (dashboard)
    ├─ components/               # Filters, KpiCards, charts/, tables, RiskList, DownloadCenter
    └─ lib/                      # api client, types, formatting
```

---

## Regenerating the projects seed CSV (Windows + Excel)

`data/seed/projects.csv` was extracted from the master workbook via Excel COM. To regenerate
after a database update, drop the new `.xlsx` in `data/` and either re-run the extraction, or let
the backend ingest it directly by pointing `EXCEL_PATH` at it (`ingest_from_excel` reads the
PROJECTS tab, header row 4, and the per-vintage issuance columns).

---

## License / attribution

Underlying project data © Berkeley Carbon Trading Project, *Voluntary Registry Offsets Database
v2026-04*, released under **CC BY 4.0**. Cite accordingly. Buyer intelligence is AI-researched
with full source attribution and confidence scoring.
