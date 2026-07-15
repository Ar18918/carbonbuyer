import { Dashboard } from "@/components/Dashboard";
import type { ProjectFilters } from "@/lib/types";

type SP = Record<string, string | string[] | undefined>;

function str(v: string | string[] | undefined): string | null {
  if (Array.isArray(v)) return v[0] ?? null;
  return v ?? null;
}
function num(v: string | string[] | undefined): number | null {
  const s = str(v);
  return s !== null && s !== "" ? Number(s) : null;
}

export default function DashboardPage({ searchParams }: { searchParams: SP }) {
  const countriesRaw = str(searchParams.countries);
  const countries = countriesRaw ? countriesRaw.split(",").map((s) => s.trim()).filter(Boolean) : null;
  const initialFilters: ProjectFilters = {
    country: str(searchParams.country),
    countries,
    project_type: str(searchParams.project_type),
    registry: str(searchParams.registry),
    region: str(searchParams.region),
    reduction_removal: str(searchParams.reduction_removal),
    vintage_year_min: num(searchParams.vintage_year_min),
    vintage_year_max: num(searchParams.vintage_year_max),
    credits_issued_min: num(searchParams.credits_issued_min),
    credits_retired_min: num(searchParams.credits_retired_min),
    include_ineligible: str(searchParams.include_ineligible) === "1",
    search: str(searchParams.search),
  };
  const model = str(searchParams.model) || "opus";
  const intensity = str(searchParams.intensity) || "standard";
  return <Dashboard initialFilters={initialFilters} initialModel={model} initialIntensity={intensity} />;
}
