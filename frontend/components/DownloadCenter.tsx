"use client";
import { Download, FileText, Users, Layers, Link2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { downloadBlob } from "@/lib/api";
import type { ProjectFilters } from "@/lib/types";

const items = [
  { key: "buyers", icon: Users, title: "Buyer Intelligence Dataset", desc: "Buyer, industry, SBTi status, purchase & retirement volumes, confidence tier.", path: "/exports/buyers.xlsx", file: "buyer_intelligence.xlsx" },
  { key: "projects", icon: Layers, title: "Project Dataset", desc: "Project details, registry, vintage, country, status, primary risk & risk flags.", path: "/exports/projects.xlsx", file: "project_dataset.xlsx" },
  { key: "mapping", icon: Link2, title: "Buyer-Project Mapping", desc: "Project → buyer, volume, confidence score, verdict, source links.", path: "/exports/buyer-project-mapping.xlsx", file: "buyer_project_mapping.xlsx" },
];

export function DownloadCenter({ filters }: { filters: ProjectFilters }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
      {items.map((it) => (
        <Card key={it.key}>
          <CardContent className="pt-5">
            <it.icon className="mb-2 text-primary" size={20} />
            <p className="text-sm font-semibold">{it.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{it.desc}</p>
            <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => downloadBlob(it.path, filters, it.file)}>
              <Download size={14} /> Download Excel
            </Button>
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardContent className="pt-5">
          <FileText className="mb-2 text-primary" size={20} />
          <p className="text-sm font-semibold">Executive Summary</p>
          <p className="mt-1 text-xs text-muted-foreground">Xynteo-branded market overview: KPIs, top buyers, confidence & key risks — as a PDF.</p>
          <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => downloadBlob("/exports/executive-summary.pdf", filters, "executive_summary.pdf")}>
            <Download size={14} /> Download PDF
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
