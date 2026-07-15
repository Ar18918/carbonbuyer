"use client";
import { Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { CountryMultiSelect } from "./CountryMultiSelect";
import type { Facets, ProjectFilters } from "@/lib/types";

const CURRENT_YEAR = 2026;
const VINTAGE_YEARS = Array.from({ length: CURRENT_YEAR - 2015 + 1 }, (_, i) => 2015 + i);

export function Filters({
  facets, filters, onChange, onRun, loading,
}: {
  facets: Facets | null;
  filters: ProjectFilters;
  onChange: (f: ProjectFilters) => void;
  onRun: () => void;
  loading: boolean;
}) {
  const set = (patch: Partial<ProjectFilters>) => onChange({ ...filters, ...patch });
  const numOrNull = (v: string) => (v === "" ? null : Number(v));

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <SlidersHorizontal size={16} className="text-primary" /> Search &amp; Filters
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <Label>Country</Label>
          <CountryMultiSelect
            options={facets?.countries ?? []}
            value={filters.countries ?? (filters.country ? [filters.country] : [])}
            onChange={(v) => set({ countries: v.length ? v : null, country: null })}
          />
        </div>
        <div>
          <Label>Project Type</Label>
          <Select value={filters.project_type ?? ""} onChange={(e) => set({ project_type: e.target.value || null })}>
            <option value="">All types</option>
            {facets?.types.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
        </div>
        <div>
          <Label>Registry</Label>
          <Select value={filters.registry ?? ""} onChange={(e) => set({ registry: e.target.value || null })}>
            <option value="">All registries</option>
            {facets?.registries.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </Select>
        </div>
        <div>
          <Label>Region</Label>
          <Select value={filters.region ?? ""} onChange={(e) => set({ region: e.target.value || null })}>
            <option value="">All regions</option>
            {facets?.regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </div>
        <div>
          <Label>Reduction vs Removal</Label>
          <Select value={filters.reduction_removal ?? ""} onChange={(e) => set({ reduction_removal: e.target.value || null })}>
            <option value="">All</option>
            {facets?.reduction_removal.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </div>
        <div>
          <Label>Vintage Year (min)</Label>
          <Select value={filters.vintage_year_min ?? ""} onChange={(e) => set({ vintage_year_min: numOrNull(e.target.value) })}>
            <option value="">≥ 2015 (default)</option>
            {VINTAGE_YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
          </Select>
        </div>
        <div>
          <Label>Credits Issued (min)</Label>
          <Input type="number" placeholder="0" value={filters.credits_issued_min ?? ""} onChange={(e) => set({ credits_issued_min: numOrNull(e.target.value) })} />
        </div>
        <div>
          <Label>Credits Retired (min)</Label>
          <Input type="number" placeholder="0" value={filters.credits_retired_min ?? ""} onChange={(e) => set({ credits_retired_min: numOrNull(e.target.value) })} />
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-2.5 top-2.5 text-muted-foreground" />
          <Input className="pl-8" placeholder="Search project name, ID or developer…" value={filters.search ?? ""} onChange={(e) => set({ search: e.target.value || null })} />
        </div>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input type="checkbox" checked={!!filters.include_ineligible} onChange={(e) => set({ include_ineligible: e.target.checked })} />
          Include ineligible (withdrawn / vintage &lt; 2015)
        </label>
        <Button onClick={onRun} disabled={loading} size="lg">
          {loading ? "Running…" : "Run Intelligence"}
        </Button>
      </div>
    </div>
  );
}
