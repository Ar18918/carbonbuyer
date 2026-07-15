"use client";
import { Download, FileText, Users, Layers, Link2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { downloadCsv, downloadText } from "@/lib/api";
import type { ProjectFilters } from "@/lib/types";

const items = [
  { key: "buyers", icon: Users, title: "Buyer Intelligence Dataset", desc: "Buyer, industry, SBTi status, purchase & retirement volumes, confidence.", file: "buyer_intelligence.csv" },
  { key: "projects", icon: Layers, title: "Project Dataset", desc: "Project details, registry, vintage, country, status, risk flags.", file: "project_dataset.csv" },
  { key: "buyer-project-mapping", icon: Link2, title: "Buyer-Project Mapping", desc: "Project → buyer, volume, confidence score, source links.", file: "buyer_project_mapping.csv" },
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
            <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => downloadCsv(it.key, filters, it.file)}>
              <Download size={14} /> Download CSV
            </Button>
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardContent className="pt-5">
          <FileText className="mb-2 text-primary" size={20} />
          <p className="text-sm font-semibold">Executive Summary</p>
          <p className="mt-1 text-xs text-muted-foreground">AI-written market overview, top buyers, trends, SBTi, key risks. Markdown → print to PDF.</p>
          <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => downloadText("/exports/executive-summary.md", filters, "executive_summary.md")}>
            <Download size={14} /> Generate Report
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
