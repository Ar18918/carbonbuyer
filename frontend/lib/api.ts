import type { AnalyzeResponse, DashboardResponse, Facets, ProjectFilters, ResearchRunOut } from "./types";

// Requests go to /api/... which next.config rewrites to the backend.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  facets: () => get<Facets>("/projects/facets"),
  stats: () => get<{ total_projects: number; eligible_projects: number }>("/projects/stats"),
  dashboard: (filters: ProjectFilters) => post<DashboardResponse>("/analytics/dashboard", filters),
  researchStatus: () => get<{ engine_enabled: boolean; model: string; note: string | null }>("/research/status"),
  analyze: (filters: ProjectFilters, opts: { force?: boolean; model?: string; intensity?: string } = {}) => {
    const qs = new URLSearchParams();
    if (opts.force) qs.set("force", "true");
    if (opts.model) qs.set("model", opts.model);
    if (opts.intensity) qs.set("intensity", opts.intensity);
    const q = qs.toString();
    return post<AnalyzeResponse>(`/research/analyze${q ? `?${q}` : ""}`, filters);
  },
  getRun: (id: number) => get<ResearchRunOut>(`/research/runs/${id}`),
  exportUrl: (kind: "buyers" | "projects" | "buyer-project-mapping", filters: ProjectFilters) => ({
    url: `${BASE}/exports/${kind}.csv`,
    filters,
  }),
  execSummaryUrl: `${BASE}/exports/executive-summary.md`,
};

// Trigger a browser download of a POST CSV endpoint.
export async function downloadCsv(kind: string, filters: ProjectFilters, filename: string) {
  const res = await fetch(`${BASE}/exports/${kind}.csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadText(path: string, filters: ProjectFilters, filename: string) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });
  const text = await res.text();
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
