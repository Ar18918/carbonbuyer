# Deploying the platform to Render (always-on, shareable URL)

Two always-on web services, no paid database. The backend uses **SQLite** and **re-seeds** the
11,343 projects + the researched market snapshots (Malawi, India) on every boot, so there's no
database to provision or pay for. Live "Analyze market" runs on your **Anthropic API key**
(kept server-side as a secret), defaulting to **Haiku + Light** to keep spend low.

## One-time: put the code on GitHub
From the `carbon-buyer-intelligence/` folder:
```bash
git init
git add .
git commit -m "Carbon Buyer Intelligence Platform"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```
> The committed seed files (`data/seed/projects.csv`, `data/seed/*_research.json`) are what the
> cloud build bakes into the image. The 16 MB source `.xlsx` is git-ignored and not needed.

## Deploy on Render (~5 clicks)
1. Go to **dashboard.render.com → New + → Blueprint**.
2. Connect your GitHub and pick the repo. Render reads **`render.yaml`** and shows two services
   (`cbi-backend`, `cbi-frontend`). Click **Apply**.
3. On **cbi-backend → Environment**, set the secret **`ANTHROPIC_API_KEY`** = your `sk-ant-api03-…`
   key, and **Save** (it redeploys).
4. Wait for both services to go live (first build ~5–10 min). Open the **cbi-frontend** URL — that's
   your permanent shareable link. Analyze works; the seeded Malawi & India markets load instantly.

## Notes
- **Free tier** spins a service down after ~15 min idle; the next visit has a ~30–60 s cold start,
  then it's fast. Upgrade a service to a paid instance to keep it always warm.
- **SQLite is ephemeral** on Render — that's fine here because the DB is fully re-seeded from the
  baked-in CSV + JSON on every boot/redeploy. Live-researched markets added at runtime are lost on
  restart; to make a researched market permanent, save its snapshot into `data/seed/` and redeploy.
- **Cost control:** defaults are Haiku + Light and `RESEARCH_AUTO_MAX_PROJECTS=10`. Change
  `RESEARCH_MODEL` / that value on the backend service to trade depth for spend.
- **Access:** the URL is public. Share narrowly; each live Analyze spends your API credit. Rotate the
  key in the Render dashboard if a link leaks.

## How the pieces fit
- `Dockerfile.backend` (context = repo root) bakes `backend/app` + `data/` into a lean image, seeds
  SQLite on boot (`entrypoint.sh`), serves FastAPI on `$PORT`.
- `frontend/Dockerfile` builds the Next.js app; it proxies `/api/*` to the backend at **runtime**
  via `app/api/[...path]/route.ts`, reading `BACKEND_URL` (injected by the Blueprint from the
  backend service). No build-time URL baking, so it "just works" on deploy.
