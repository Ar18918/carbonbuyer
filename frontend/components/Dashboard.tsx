"use client";
import * as React from "react";
import { Leaf, Info, Users, Loader2, AlertTriangle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { AnalyzeResponse, DashboardResponse, Facets, ProjectFilters, ResearchRunOut } from "@/lib/types";
import { Filters } from "./Filters";
import { KpiCards } from "./KpiCards";
import { TopBuyersTable, RepeatBuyersTable, IndustryTable } from "./BuyerTables";
import { ProjectTable } from "./ProjectTable";
import { RiskList } from "./RiskList";
import { DownloadCenter } from "./DownloadCenter";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Select } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { HBarChart, VBarChart, DonutChart, KeyedDonut, AreaLineChart } from "./charts/Charts";
import { SEMANTIC, SBTI_COLORS } from "./charts/palette";
import { formatNumber } from "@/lib/format";

function ChartCard({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle>{hint && <p className="text-xs text-muted-foreground">{hint}</p>}</CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ResearchBanner({ r, segment, onRetry }: { r: ResearchUI; segment: string; onRetry: () => void }) {
  if (r.state === "idle" || r.state === "done") return null;

  if (r.state === "checking" || r.state === "running") {
    const rr = r.run;
    return (
      <div className="card-grad flex items-start gap-3 rounded-lg border border-primary/30 p-4">
        <Loader2 className="mt-0.5 shrink-0 animate-spin text-primary" size={18} />
        <div>
          <p className="text-sm font-semibold">Running AI buyer research for {segment}…</p>
          <p className="mt-1 text-xs text-muted-foreground">
            The Claude research engine is discovering buyers, adversarially verifying each claim against sources, and enriching
            SBTi &amp; industry. This can take a few minutes. Project analytics below are live now — buyers, SBTi and risk populate here when ready.
          </p>
          {rr && (rr.projects_researched > 0 || rr.buyers_found > 0) && (
            <p className="mt-1.5 text-xs font-medium text-primary">
              {rr.projects_researched} projects researched · {rr.buyers_found} buyers found so far
            </p>
          )}
        </div>
      </div>
    );
  }

  if (r.state === "disabled") {
    return (
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">
        <b>Live research is off.</b> {r.note || "Set ANTHROPIC_API_KEY on the backend"} to auto-discover buyers for any market.
        The project list and deterministic analytics below are live; the <b>Malawi · Afforestation/Reforestation</b> MVP ships fully-researched buyer data.
      </div>
    );
  }

  if (r.state === "needs_segment") {
    return (
      <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        Select both a <b>country</b> and a <b>project type</b> to run AI buyer research. Showing deterministic project analytics for the current filters.
      </div>
    );
  }

  if (r.state === "no_projects") {
    return (
      <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        No eligible projects match this segment, so there is nothing to research. Widen the filters or enable “include ineligible”.
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-rose-300 bg-rose-50 p-3 text-xs text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">
      <span className="flex items-center gap-2"><AlertTriangle size={14} /> Research failed{r.note ? `: ${r.note}` : ""}.</span>
      <button onClick={onRetry} className="inline-flex items-center gap-1 rounded-md border border-current px-2 py-1 font-medium">
        <RefreshCw size={12} /> Retry
      </button>
    </div>
  );
}

type ResearchUI = {
  state: "idle" | "checking" | "running" | "done" | "disabled" | "needs_segment" | "no_projects" | "error";
  runId: number | null;
  run?: ResearchRunOut | null;
  note?: string | null;
};

export function Dashboard({
  initialFilters, initialModel = "haiku", initialIntensity = "light",
}: { initialFilters: ProjectFilters; initialModel?: string; initialIntensity?: string }) {
  const [facets, setFacets] = React.useState<Facets | null>(null);
  const [filters, setFilters] = React.useState<ProjectFilters>(initialFilters);
  const [data, setData] = React.useState<DashboardResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);
  const [engine, setEngine] = React.useState<{ engine_enabled: boolean; model: string } | null>(null);
  const [research, setResearch] = React.useState<ResearchUI>({ state: "idle", runId: null });
  const [model, setModel] = React.useState(initialModel);
  const [intensity, setIntensity] = React.useState(initialIntensity);
  const pollRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  // Kept in a ref so changing model/intensity never re-triggers the auto-run effect —
  // it only affects the next explicit "Re-run".
  const settingsRef = React.useRef({ model: initialModel, intensity: initialIntensity });
  React.useEffect(() => { settingsRef.current = { model, intensity }; }, [model, intensity]);

  const stopPoll = React.useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  // Re-fetch the dashboard payload only (does not re-trigger research).
  const refetch = React.useCallback(async (f: ProjectFilters) => {
    try { setData(await api.dashboard(f)); } catch { /* keep prior data */ }
  }, []);

  const startPoll = React.useCallback((id: number, f: ProjectFilters) => {
    stopPoll();
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts += 1;
      try {
        const r = await api.getRun(id);
        setResearch((s) => ({ ...s, run: r }));
        if (r.status === "completed") {
          stopPoll();
          setResearch({ state: "done", runId: id, run: r });
          refetch(f);
        } else if (r.status === "failed") {
          stopPoll();
          setResearch({ state: "error", runId: id, run: r, note: r.error });
        }
      } catch { /* transient; keep polling */ }
      if (attempts > 90) stopPoll(); // ~6 min safety cap (4s interval)
    }, 4000);
  }, [refetch, stopPoll]);

  // Decide whether to kick off AI research for the current segment.
  const ensureResearch = React.useCallback(async (f: ProjectFilters, dash: DashboardResponse) => {
    if (dash.buyer_count > 0) { setResearch({ state: "idle", runId: null }); return; }
    const hasCountry = !!(f.countries?.length || f.country);
    if (!hasCountry || !f.project_type) { setResearch({ state: "needs_segment", runId: null }); return; }
    if (dash.projects.length === 0) { setResearch({ state: "no_projects", runId: null }); return; }
    setResearch({ state: "checking", runId: null });
    try {
      const res: AnalyzeResponse = await api.analyze(f, settingsRef.current);
      if (res.status === "ready") { setResearch({ state: "idle", runId: null }); refetch(f); return; }
      if (res.status === "started" || res.status === "running") {
        setResearch({ state: "running", runId: res.run_id });
        if (res.run_id) startPoll(res.run_id, f);
        return;
      }
      setResearch({ state: res.status as ResearchUI["state"], runId: null, note: res.note });
    } catch {
      setResearch({ state: "error", runId: null, note: "Could not reach the research engine." });
    }
  }, [refetch, startPoll]);

  const run = React.useCallback(async (f: ProjectFilters) => {
    setLoading(true); setErr(null);
    try {
      const d = await api.dashboard(f);
      setData(d);
      ensureResearch(f, d);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [ensureResearch]);

  // Manual re-run (force a fresh research pass even if buyers already exist).
  const rerun = React.useCallback(async () => {
    if (!filters.country || !filters.project_type) return;
    setResearch({ state: "checking", runId: null });
    try {
      const res = await api.analyze(filters, { force: true, ...settingsRef.current });
      if (res.run_id) { setResearch({ state: "running", runId: res.run_id }); startPoll(res.run_id, filters); }
      else setResearch({ state: res.status as ResearchUI["state"], runId: null, note: res.note });
    } catch {
      setResearch({ state: "error", runId: null, note: "Could not reach the research engine." });
    }
  }, [filters, startPoll]);

  React.useEffect(() => {
    api.facets().then(setFacets).catch(() => {});
    api.researchStatus().then(setEngine).catch(() => {});
    run(initialFilters);
    return () => stopPoll();
  }, [run, initialFilters, stopPoll]);

  const segLabel = (filters.countries?.length ? filters.countries.join(", ") : filters.country) || "All countries";
  const hasSegment = !!(filters.countries?.length || filters.country) && !!filters.project_type;

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <a href="/" className="rounded-xl bg-primary p-2 text-primary-foreground" title="New search"><Leaf size={22} /></a>
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              {segLabel} · {filters.project_type || "All project types"}
            </h1>
            <p className="text-xs text-muted-foreground">Carbon Credit Buyer Intelligence Platform</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {engine && (
            <div className="flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs text-muted-foreground">
              <span className={`h-2 w-2 rounded-full ${engine.engine_enabled ? "bg-emerald-500" : "bg-amber-500"}`} />
              {engine.engine_enabled ? `Live research engine: ${engine.model}` : "Research engine idle — showing seeded snapshot"}
            </div>
          )}
          <a href="/" className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted">← New search</a>
        </div>
      </header>

      <Filters facets={facets} filters={filters} onChange={setFilters} onRun={() => run(filters)} loading={loading} />

      {err && <div className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40">{err}. Is the backend running at /api?</div>}

      {data && (
        <>
          <div className="flex items-start justify-between gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <Info size={14} className="mt-0.5 shrink-0 text-primary" />
              <span>
                Buyer intelligence is compiled from public retirement disclosures, registry records, corporate/ESG reports, press releases and market databases — every buyer and risk carries a source link and confidence score.
                Pre-issuance projects surface buyers as forward purchasers / offtakers / funders rather than retirements.
              </span>
            </div>
            {hasSegment && (
              <div className="flex shrink-0 flex-wrap items-center gap-2" title="Model + intensity control speed, depth and rate-limit usage">
                <Select value={model} onChange={(e) => setModel(e.target.value)} className="h-8 w-auto text-xs">
                  <option value="haiku">Haiku</option>
                  <option value="sonnet">Sonnet</option>
                  <option value="opus">Opus</option>
                </Select>
                <Select value={intensity} onChange={(e) => setIntensity(e.target.value)} className="h-8 w-auto text-xs">
                  <option value="light">Light</option>
                  <option value="standard">Standard</option>
                  <option value="deep">Deep</option>
                </Select>
                <button
                  onClick={rerun}
                  disabled={research.state === "running" || research.state === "checking"}
                  className="inline-flex items-center gap-1 rounded-md border border-primary/40 px-2 py-1 font-medium text-primary hover:bg-primary/10 disabled:opacity-50"
                >
                  <RefreshCw size={12} className={research.state === "running" ? "animate-spin" : ""} /> {data.buyer_count > 0 ? "Re-run" : "Run research"}
                </button>
              </div>
            )}
          </div>

          <ResearchBanner
            r={research}
            segment={`${segLabel} · ${filters.project_type || "All project types"}`}
            onRetry={rerun}
          />

          <KpiCards kpis={data.kpis} />

          {/* Row: distribution donuts + buyer count */}
          <div className="grid gap-3 lg:grid-cols-4">
            <Card className="card-grad">
              <CardHeader><CardTitle>Buyer Count</CardTitle></CardHeader>
              <CardContent className="flex items-center gap-3">
                <Users className="text-primary" size={26} />
                <span className="text-4xl font-bold">{formatNumber(data.buyer_count)}</span>
              </CardContent>
            </Card>
            <ChartCard title="Buyer Frequency" hint="One-time vs repeat buyers">
              <DonutChart data={data.buyer_frequency} colors={[SEMANTIC.oneTime, SEMANTIC.repeat]} />
            </ChartCard>
            <ChartCard title="Retirement Split" hint="Retired vs non-retired volume">
              <DonutChart data={data.retirement_split} colors={[SEMANTIC.retired, SEMANTIC.nonRetired]} />
            </ChartCard>
            <ChartCard title="SBTi Alignment" hint="Aligned / Not / Unknown">
              <KeyedDonut data={data.sbti_alignment} colorMap={SBTI_COLORS} />
            </ChartCard>
          </div>

          {/* Row: time series */}
          <div className="grid gap-3 lg:grid-cols-2">
            <ChartCard title="Vintage Activity" hint="Buyer volume by project vintage year">
              <VBarChart data={data.vintage_activity} color={SEMANTIC.primary} />
            </ChartCard>
            <ChartCard title="Retirement Activity" hint="Retirement / transaction volume by year">
              <AreaLineChart data={data.retirement_activity} />
            </ChartCard>
          </div>

          {/* Row: attribution bars */}
          <div className="grid gap-3 lg:grid-cols-2">
            <ChartCard title="Buyer Volume by Region"><HBarChart data={data.volume_by_region} /></ChartCard>
            <ChartCard title="Buyer Volume by Country"><HBarChart data={data.volume_by_country} /></ChartCard>
            <ChartCard title="Buyer Volume by Reduction vs Removal"><HBarChart data={data.volume_by_reduction_removal} /></ChartCard>
            <ChartCard title="Buyer Volume by Registry"><HBarChart data={data.volume_by_registry} /></ChartCard>
          </div>

          {/* Tables */}
          <Card>
            <CardContent className="pt-5">
              <Tabs defaultValue="top">
                <TabsList>
                  <TabsTrigger value="top">Top Buyers</TabsTrigger>
                  <TabsTrigger value="repeat">Repeat Buyers</TabsTrigger>
                  <TabsTrigger value="industry">Industry</TabsTrigger>
                  <TabsTrigger value="projects">Projects ({data.projects.length})</TabsTrigger>
                  <TabsTrigger value="risks">Risk Flags ({data.risks.length})</TabsTrigger>
                </TabsList>
                <TabsContent value="top"><TopBuyersTable buyers={data.top_buyers} /></TabsContent>
                <TabsContent value="repeat"><RepeatBuyersTable buyers={data.repeat_buyers} /></TabsContent>
                <TabsContent value="industry">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <VBarChart data={data.industry_segmentation.map((r) => ({ name: r.name, value: r.value }))} />
                    <IndustryTable rows={data.industry_segmentation} />
                  </div>
                </TabsContent>
                <TabsContent value="projects"><ProjectTable projects={data.projects} /></TabsContent>
                <TabsContent value="risks"><RiskList risks={data.risks} projects={data.projects} /></TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Download centre */}
          <div>
            <h2 className="mb-2 mt-2 text-sm font-semibold">Download Centre</h2>
            <DownloadCenter filters={filters} />
          </div>

          <footer className="pb-8 pt-4 text-center text-xs text-muted-foreground">
            Project data aggregated from the major voluntary carbon registries (Verra, Gold Standard, CAR, ACR, Isometric, ART).
            Buyer intelligence is AI-researched with source attribution &amp; confidence scoring.
            <span className="mt-1 block opacity-60">Registry compilation via the Voluntary Registry Offsets Database (CC BY 4.0).</span>
          </footer>
        </>
      )}
    </div>
  );
}
