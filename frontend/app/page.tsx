"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { Leaf, ArrowRight, Database, Sparkles, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Facets } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Select, Label } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { CountryMultiSelect } from "@/components/CountryMultiSelect";
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
  const [type, setType] = React.useState("");
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

  function analyze(over?: { countries?: string[]; project_type?: string; include_ineligible?: boolean }) {
    const params = new URLSearchParams();
    const cs = over?.countries ?? countries;
    const t = over?.project_type ?? type;
    if (cs.length) params.set("countries", cs.join(","));
    if (t) params.set("project_type", t);
    if (registry) params.set("registry", registry);
    if (region) params.set("region", region);
    if (rr) params.set("reduction_removal", rr);
    if (vintage) params.set("vintage_year_min", vintage);
    if (over?.include_ineligible ?? includeIneligible) params.set("include_ineligible", "1");
    params.set("model", model);
    params.set("intensity", intensity);
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
              <Label>Project Type</Label>
              <Select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="">All project types</option>
                {facets?.types.map((t) => <option key={t} value={t}>{t}</option>)}
              </Select>
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

          <div className="mt-5 flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {stats ? <>{formatNumber(stats.total_projects)} projects · {formatNumber(stats.eligible_projects)} eligible</> : "Loading dataset…"}
            </p>
            <Button size="lg" onClick={() => analyze()}>
              Analyze market <ArrowRight size={16} />
            </Button>
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
