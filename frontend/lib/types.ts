// API contract types — mirror of backend/app/schemas.py

export interface ProjectFilters {
  country?: string | null;
  countries?: string[] | null;
  project_type?: string | null;
  registry?: string | null;
  region?: string | null;
  reduction_removal?: string | null;
  vintage_year_min?: number | null;
  vintage_year_max?: number | null;
  credits_issued_min?: number | null;
  credits_issued_max?: number | null;
  credits_retired_min?: number | null;
  credits_retired_max?: number | null;
  include_ineligible?: boolean;
  search?: string | null;
}

export interface ProjectOut {
  id: number;
  project_id: string;
  project_name: string;
  registry: string;
  voluntary_status: string;
  scope: string;
  type: string;
  reduction_removal: string;
  methodology: string;
  region: string;
  country: string;
  state: string;
  developer: string;
  credits_issued: number;
  credits_retired: number;
  credits_remaining: number;
  first_vintage_year: number | null;
  is_eligible: boolean;
  risk_count: number;
  buyer_count: number;
}

export interface BuyerOut {
  id: number;
  name: string;
  entity_type: string;
  industry: string;
  industry_group: string;
  industry_confidence: string;
  hq_country: string | null;
  sbti_status: string;
  sbti_alignment: string;
  sbti_validation_year: string | null;
  sbti_target_year: string | null;
  profile_summary: string;
  source_urls: string[];
  total_estimated_volume: number;
  total_retired_volume: number;
  total_non_retired_volume: number;
  num_projects: number;
  num_countries: number;
  num_project_types: number;
  num_purchase_years: number;
  repeat_purchase_count: number;
  total_repeat_volume: number;
  repeat_buyer_score: number;
  is_repeat_buyer: boolean;
}

export interface RiskFlagOut {
  id: number;
  project_id: number;
  risk_category: string;
  risk_description: string;
  severity_score: number;
  source_url: string;
  date: string | null;
  ai_summary: string;
}

export interface KPIs {
  total_buyers: number;
  total_estimated_volume: number;
  total_projects: number;
  repeat_buyer_pct: number;
  sbti_aligned_pct: number;
}

export interface NameValue {
  name: string;
  value: number;
}
export interface NameValue2 extends NameValue {
  value2: number;
}

export interface DashboardResponse {
  filters: ProjectFilters;
  kpis: KPIs;
  buyer_count: number;
  top_buyers: BuyerOut[];
  repeat_buyers: BuyerOut[];
  buyer_frequency: NameValue[];
  vintage_activity: NameValue[];
  retirement_activity: NameValue[];
  retirement_split: NameValue[];
  volume_by_region: NameValue[];
  volume_by_country: NameValue[];
  volume_by_reduction_removal: NameValue[];
  volume_by_registry: NameValue[];
  sbti_alignment: NameValue[];
  industry_segmentation: NameValue2[];
  projects: ProjectOut[];
  risks: RiskFlagOut[];
}

export interface Facets {
  countries: string[];
  types: string[];
  regions: string[];
  registries: { value: string; label: string }[];
  reduction_removal: string[];
}

export interface ResearchRunOut {
  id: number;
  country: string | null;
  project_type: string | null;
  status: string; // queued | running | completed | failed
  model: string;
  projects_researched: number;
  buyers_found: number;
  error: string | null;
}

export interface AnalyzeResponse {
  status: "ready" | "running" | "started" | "needs_segment" | "no_projects" | "disabled";
  run_id: number | null;
  note: string | null;
}
