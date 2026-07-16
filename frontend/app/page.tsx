"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { Leaf, ArrowRight, Database, Sparkles, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Facets } from "@/lib/types";
import { Select, Label } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { CountryMultiSelect } from "@/components/CountryMultiSelect";
import { MultiSelect } from "@/components/MultiSelect";
import { formatNumber } from "@/lib/format";

const CURRENT_YEAR = 2026;
const VINTAGE_YEARS = Array.from({ length: CURRENT_YEAR - 2015 + 1 }, (_, i) => 2015 + i);

// Segments that ship with fully-researched buyer intelligence in the seed snapshot.
const RESEARCHED = [
  { country: "Malawi", project_type: "Afforestation/Reforestation", label: "Malawi · Afforestation/Reforestation" },
  { country: "India", project_type: "Biochar", label: "India · Biochar" },
];

export default function Landing() {
  const router = useRouter();
  const [facets, setFacets] = React.useState<Facets | null>(null);
  const [stats, setStats] = React.useState<{ total_projects: number; eligible_projects: number } | null>(null);
  const [countries, setCountries] = React.useState<string[]>([]);
  const [types, setTypes] = React.useState<string[]>([]);
  const [registry, setRegistry] = React.useState("");
  const [region, setRegion] = React.useState("");
  const [rr, setRr] = React.useState("");
  const [vintage, setVintage] = React.useState("");
  const [includeIneligible, setIncludeIneligible] = React.useState(false);
  // Research always runs on Claude Opus deep research at standard intensity (no user-facing knobs).
  const model = "opus";
  const intensity = "standard";

  React.useEffect(() => {
    api.facets().then(setFacets).catch(() => {});
    api.stats().then(setStats).catch(() => {});
  }, []);

  function analyze(
    over?: { countries?: string[]; project_type?: string; include_ineligible?: boolean },
    source: "registry" | "all" = "all",
  ) {
    const params = new URLSearchParams();
    const cs = over?.countries ?? countries;
    const ts = over?.project_type ? [over.project_type] : types;
    if (cs.length) params.set("countries", cs.join(","));
    if (ts.length) params.set("project_types", ts.join(","));
    if (registry) params.set("registry", registry);
    if (region) params.set("region", region);
    if (rr) params.set("reduction_removal", rr);
    if (vintage) params.set("vintage_year_min", vintage);
    if (over?.include_ineligible ?? includeIneligible) params.set("include_ineligible", "1");
    params.set("model", model);
    params.set("intensity", intensity);
    params.set("source", source);
    router.push(`/dashboard?${params.toString()}`);
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:py-16">
      {/* Hero */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-primary p-2.5 text-primary-foreground"><Leaf size={26} /></div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Identify the buyers behind any carbon market</h1>
          <p className="text-sm text-muted-foreground">Pick a country and project type — the engine surfaces likely buyers, volumes, SBTi alignment and risk, each with cited sources.</p>
        </div>
      </div>

      {/* Selection card */}
      <Card className="mt-8">
        <CardContent className="pt-6">
          <p className="mb-4 text-sm font-semibold">Select a market to analyze</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label>Country <span className="font-normal opacity-70">(add one or more)</span></Label>
              <CountryMultiSelect options={facets?.countries ?? []} value={countries} onChange={setCountries} />
            </div>
            <div>
              <Label>Project Type <span className="font-normal opacity-70">(one or more)</span></Label>
              <MultiSelect
                options={facets?.types ?? []}
                value={types}
                onChange={setTypes}
                allLabel="All project types"
                addLabel="Add another type…"
              />
            </div>
          </div>

          <details className="mt-4">
            <summary className="cursor-pointer text-xs font-medium text-muted-foreground">Optional filters</summary>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <Label>Registry</Label>
                <Select value={registry} onChange={(e) => setRegistry(e.target.value)}>
                  <option value="">All</option>
                  {facets?.registries.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </Select>
              </div>
              <div>
                <Label>Region</Label>
                <Select value={region} onChange={(e) => setRegion(e.target.value)}>
                  <option value="">All</option>
                  {facets?.regions.map((r) => <option key={r} value={r}>{r}</option>)}
                </Select>
              </div>
              <div>
                <Label>Reduction vs Removal</Label>
                <Select value={rr} onChange={(e) => setRr(e.target.value)}>
                  <option value="">All</option>
                  {facets?.reduction_removal.map((r) => <option key={r} value={r}>{r}</option>)}
                </Select>
              </div>
              <div>
                <Label>Vintage Year (min)</Label>
                <Select value={vintage} onChange={(e) => setVintage(e.target.value)}>
                  <option value="">≥ 2015 (default)</option>
                  {VINTAGE_YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
                </Select>
              </div>
            </div>
            <label className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <input type="checkbox" checked={includeIneligible} onChange={(e) => setIncludeIneligible(e.target.checked)} />
              Include ineligible projects (withdrawn / cancelled / vintage &lt; 2015)
            </label>
          </details>

          <div className="mt-5 space-y-3">
            <p className="text-xs text-muted-foreground">
              {stats ? <>{formatNumber(stats.total_projects)} projects · {formatNumber(stats.eligible_projects)} eligible</> : "Loading dataset…"}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                onClick={() => analyze(undefined, "registry")}
                className="group flex flex-col items-start gap-1 rounded-lg bg-primary p-4 text-left text-primary-foreground shadow-sm transition hover:opacity-90"
              >
                <span className="flex items-center gap-2 font-semibold">
                  <Database size={17} /> Registered buyers
                  <ArrowRight size={15} className="transition group-hover:translate-x-0.5" />
                </span>
                <span className="text-xs opacity-90">
                  Instant, no AI. Entities that have <b>retired</b> credits from these projects, from public registry records (OffsetsDB).
                </span>
              </button>
              <button
                onClick={() => analyze(undefined, "all")}
                className="group flex flex-col items-start gap-1 rounded-lg border border-primary/40 p-4 text-left transition hover:bg-primary/5"
              >
                <span className="flex items-center gap-2 font-semibold text-primary">
                  <Sparkles size={17} /> Deep research (Opus)
                  <ArrowRight size={15} className="transition group-hover:translate-x-0.5" />
                </span>
                <span className="text-xs text-muted-foreground">
                  Builds on the registered buyers, then uses Claude to add offtakers/funders plus SBTi &amp; risk intelligence.
                </span>
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Researched example */}
      <div className="mt-6">
        <p className="mb-2 text-xs font-semibold text-muted-foreground">Fully-researched example (buyer data included)</p>
        <div className="flex flex-wrap gap-2">
          {RESEARCHED.map((s) => (
            <button
              key={s.label}
              onClick={() => analyze({ countries: [s.country], project_type: s.project_type, include_ineligible: true })}
              className="inline-flex items-center gap-2 rounded-full border bg-card px-4 py-2 text-sm font-medium shadow-sm hover:bg-muted"
            >
              <Sparkles size={14} className="text-primary" /> {s.label} <ArrowRight size={14} />
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Other markets show the full project list + deterministic analytics immediately; buyer intelligence is generated
          on demand by the AI research engine (a Claude API key enables live research).
        </p>
      </div>

      {/* What you get */}
      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        <Feature icon={<Database size={18} />} title="Real registry data" body="11,343 projects across the major voluntary carbon registries — Verra, Gold Standard, CAR, ACR, Isometric, ART." />
        <Feature icon={<Sparkles size={18} />} title="AI-researched buyers" body="Buyers, offtakers and funders discovered from disclosures, registries, ESG reports & press — with source links and confidence scores." />
        <Feature icon={<ShieldCheck size={18} />} title="SBTi & risk intelligence" body="SBTi alignment per buyer plus project red-flags: integrity, additionality, permanence, community and regulatory risk." />
      </div>

      <footer className="mt-12 text-center text-xs text-muted-foreground">
        Project data aggregated from public voluntary carbon registries.
        <span className="opacity-60"> Registry compilation via the Voluntary Registry Offsets Database (CC BY 4.0).</span>
      </footer>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-2 inline-flex rounded-lg bg-primary/10 p-2 text-primary">{icon}</div>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs text-muted-foreground">{body}</p>
    </div>
  );
}
