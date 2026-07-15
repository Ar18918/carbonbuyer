import { Badge } from "@/components/ui/badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { ProjectOut } from "@/lib/types";
import { formatNumber } from "@/lib/format";

function riskVariant(sev: number | null | undefined) {
  if (sev == null) return "outline" as const;
  if (sev >= 70) return "danger" as const;
  if (sev >= 50) return "medium" as const;
  return "low" as const;
}

export function ProjectTable({ projects }: { projects: ProjectOut[] }) {
  if (!projects.length) return <div className="py-10 text-center text-sm text-muted-foreground">No matching projects.</div>;
  return (
    <Table>
      <THead>
        <TR>
          <TH>Project ID</TH><TH>Name</TH><TH>Registry</TH><TH>Status</TH><TH>Vintage</TH>
          <TH className="text-right">Issued</TH><TH className="text-right">Retired</TH><TH>Developer</TH><TH>Buyers</TH><TH>Risks</TH><TH>Primary Risk</TH>
        </TR>
      </THead>
      <TBody>
        {projects.map((p) => (
          <TR key={p.id}>
            <TD className="font-mono text-xs">{p.project_id}</TD>
            <TD className="max-w-[260px] truncate" title={p.project_name}>{p.project_name}</TD>
            <TD>{p.registry}</TD>
            <TD><span className="text-xs text-muted-foreground">{p.voluntary_status}</span></TD>
            <TD>{p.first_vintage_year ?? "—"}</TD>
            <TD className="text-right tabular-nums">{formatNumber(p.credits_issued)}</TD>
            <TD className="text-right tabular-nums">{formatNumber(p.credits_retired)}</TD>
            <TD className="max-w-[180px] truncate" title={p.developer}>{p.developer}</TD>
            <TD>{p.buyer_count > 0 ? <Badge variant="high">{p.buyer_count}</Badge> : <span className="text-muted-foreground">—</span>}</TD>
            <TD>{p.risk_count > 0 ? <Badge variant="danger">{p.risk_count}</Badge> : <span className="text-muted-foreground">—</span>}</TD>
            <TD className="max-w-[200px]">
              {p.primary_risk
                ? <Badge variant={riskVariant(p.primary_risk_severity)} title={`Severity ${Math.round(p.primary_risk_severity ?? 0)}/100`}>{p.primary_risk}</Badge>
                : <span className="text-muted-foreground">—</span>}
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}
