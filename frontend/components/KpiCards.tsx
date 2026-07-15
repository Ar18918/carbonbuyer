import { Users, Layers, TrendingUp, Repeat, BadgeCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { KPIs } from "@/lib/types";
import { formatNumber, formatPct, formatVolume } from "@/lib/format";

function Kpi({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <Card className="card-grad p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">{value}</p>
          {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
        </div>
        <div className="rounded-lg bg-primary/10 p-2 text-primary">{icon}</div>
      </div>
    </Card>
  );
}

export function KpiCards({ kpis }: { kpis: KPIs }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      <Kpi icon={<Users size={18} />} label="Total Buyers Identified" value={formatNumber(kpis.total_buyers)} />
      <Kpi icon={<TrendingUp size={18} />} label="Est. Buyer Volume" value={`${formatVolume(kpis.total_estimated_volume)}`} sub="tCO₂e" />
      <Kpi icon={<Layers size={18} />} label="Projects Included" value={formatNumber(kpis.total_projects)} />
      <Kpi icon={<Repeat size={18} />} label="Repeat Buyers" value={formatPct(kpis.repeat_buyer_pct)} />
      <Kpi icon={<BadgeCheck size={18} />} label="SBTi-Aligned Buyers" value={formatPct(kpis.sbti_aligned_pct)} />
    </div>
  );
}
