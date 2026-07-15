import { ExternalLink, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ProjectOut, RiskFlagOut } from "@/lib/types";

function sev(score: number) {
  if (score >= 75) return { label: "Critical", variant: "danger" as const };
  if (score >= 50) return { label: "High", variant: "medium" as const };
  return { label: "Moderate", variant: "low" as const };
}

export function RiskList({ risks, projects }: { risks: RiskFlagOut[]; projects: ProjectOut[] }) {
  if (!risks.length)
    return <div className="py-10 text-center text-sm text-muted-foreground">No material red flags surfaced for this segment.</div>;
  const pmap = new Map(projects.map((p) => [p.id, p]));
  const sorted = [...risks].sort((a, b) => b.severity_score - a.severity_score);
  return (
    <div className="space-y-2">
      {sorted.map((r) => {
        const s = sev(r.severity_score);
        const proj = pmap.get(r.project_id);
        return (
          <div key={r.id} className="rounded-lg border bg-card p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} className="text-amber-500" />
                <span className="text-sm font-medium">{r.risk_category.replace(/_/g, " ")}</span>
                <Badge variant={s.variant}>{s.label} · {Math.round(r.severity_score)}</Badge>
                {proj && <span className="text-xs font-mono text-muted-foreground">{proj.project_id}</span>}
              </div>
              {r.date && <span className="text-xs text-muted-foreground">{r.date}</span>}
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">{r.ai_summary}</p>
            {r.source_url && (
              <a href={r.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline">
                Source <ExternalLink size={11} />
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
