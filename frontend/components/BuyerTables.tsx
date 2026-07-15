import { Badge, confidenceVariant, sbtiVariant } from "@/components/ui/badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { BuyerOut } from "@/lib/types";
import { formatNumber, tCO2e } from "@/lib/format";

export function TopBuyersTable({ buyers }: { buyers: BuyerOut[] }) {
  if (!buyers.length) return <Empty />;
  return (
    <Table>
      <THead>
        <TR>
          <TH>#</TH><TH>Buyer</TH><TH>Industry</TH><TH className="text-right">Est. Volume</TH>
          <TH className="text-right">Retired</TH><TH className="text-right">Projects</TH><TH>Confidence</TH><TH>SBTi</TH>
        </TR>
      </THead>
      <TBody>
        {buyers.map((b, i) => (
          <TR key={b.id}>
            <TD className="text-muted-foreground">{i + 1}</TD>
            <TD>
              <div className="font-medium" title={b.profile_summary}>{b.name}</div>
              {b.hq_country && <div className="text-xs text-muted-foreground">{b.hq_country}</div>}
            </TD>
            <TD><Badge variant="outline">{b.industry}</Badge></TD>
            <TD className="text-right tabular-nums">{tCO2e(b.total_estimated_volume)}</TD>
            <TD className="text-right tabular-nums">{tCO2e(b.total_retired_volume)}</TD>
            <TD className="text-right tabular-nums">{b.num_projects}</TD>
            <TD><Badge variant={confidenceVariant(b.confidence_tier)} title={`Confidence score ${Math.round(b.confidence_score)}/100`}>{b.confidence_tier}</Badge></TD>
            <TD><Badge variant={sbtiVariant(b.sbti_alignment)}>{b.sbti_alignment.replace("SBTi ", "")}</Badge></TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export function RepeatBuyersTable({ buyers }: { buyers: BuyerOut[] }) {
  if (!buyers.length) return <Empty label="No repeat buyers detected in this segment." />;
  return (
    <Table>
      <THead>
        <TR>
          <TH>Buyer</TH><TH className="text-right">Purchase Events</TH><TH className="text-right">Total Volume</TH><TH className="text-right">Repeat Score</TH>
        </TR>
      </THead>
      <TBody>
        {buyers.map((b) => (
          <TR key={b.id}>
            <TD className="font-medium">{b.name}</TD>
            <TD className="text-right tabular-nums">{b.repeat_purchase_count + 1}</TD>
            <TD className="text-right tabular-nums">{tCO2e(b.total_estimated_volume)}</TD>
            <TD className="text-right">
              <span className="inline-flex items-center gap-2">
                <span className="tabular-nums">{formatNumber(b.repeat_buyer_score)}</span>
                <span className="h-1.5 w-16 overflow-hidden rounded bg-muted">
                  <span className="block h-full bg-primary" style={{ width: `${Math.min(b.repeat_buyer_score, 100)}%` }} />
                </span>
              </span>
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export function IndustryTable({ rows }: { rows: { name: string; value: number; value2: number }[] }) {
  if (!rows.length) return <Empty />;
  const totalVol = rows.reduce((s, r) => s + r.value2, 0) || 1;
  return (
    <Table>
      <THead><TR><TH>Industry</TH><TH className="text-right">Buyers</TH><TH className="text-right">Volume</TH><TH className="text-right">Volume Share</TH></TR></THead>
      <TBody>
        {rows.map((r) => (
          <TR key={r.name}>
            <TD className="font-medium">{r.name}</TD>
            <TD className="text-right tabular-nums">{r.value}</TD>
            <TD className="text-right tabular-nums">{tCO2e(r.value2)}</TD>
            <TD className="text-right tabular-nums">{((r.value2 / totalVol) * 100).toFixed(1)}%</TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

function Empty({ label = "No buyers identified for this segment yet." }: { label?: string }) {
  return <div className="py-10 text-center text-sm text-muted-foreground">{label}</div>;
}
