"use client";
import * as React from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { NameValue } from "@/lib/types";
import { colorAt, PALETTE } from "./palette";
import { formatVolume } from "@/lib/format";

const AXIS = "#94a3b8";
const GRID = "#e2e8f0";

const tooltipStyle = {
  background: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
  color: "hsl(var(--foreground))",
};

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
      {label}
    </div>
  );
}

export function HBarChart({ data, color, valueLabel = "Volume" }: { data: NameValue[]; color?: string; valueLabel?: string }) {
  if (!data?.length) return <EmptyState label="No data for this segment" />;
  const height = Math.max(180, data.length * 34 + 30);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} strokeOpacity={0.4} />
        <XAxis type="number" tickFormatter={formatVolume} tick={{ fontSize: 11, fill: AXIS }} />
        <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11, fill: AXIS }} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [formatVolume(v), valueLabel]} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((_, i) => <Cell key={i} fill={color || colorAt(i)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VBarChart({ data, color }: { data: NameValue[]; color?: string }) {
  if (!data?.length) return <EmptyState label="No data for this segment" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ left: 4, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke={GRID} strokeOpacity={0.4} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: AXIS }} interval={0} angle={-20} textAnchor="end" height={60} />
        <YAxis tickFormatter={formatVolume} tick={{ fontSize: 11, fill: AXIS }} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatVolume(v)} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => <Cell key={i} fill={color || colorAt(i)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, colors }: { data: NameValue[]; colors?: string[] }) {
  const nonzero = data?.filter((d) => d.value > 0) ?? [];
  if (!nonzero.length) return <EmptyState label="No data for this segment" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={nonzero} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
          {nonzero.map((_, i) => <Cell key={i} fill={colors?.[i] ?? colorAt(i)} />)}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatVolume(v)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function KeyedDonut({ data, colorMap }: { data: NameValue[]; colorMap: Record<string, string> }) {
  const nonzero = data?.filter((d) => d.value > 0) ?? [];
  if (!nonzero.length) return <EmptyState label="No data for this segment" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={nonzero} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
          {nonzero.map((d, i) => <Cell key={i} fill={colorMap[d.name] ?? colorAt(i)} />)}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => Math.round(v).toString()} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function AreaLineChart({ data, color = PALETTE[0] }: { data: NameValue[]; color?: string }) {
  if (!data?.length) return <EmptyState label="No data for this segment" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ left: 4, right: 12, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke={GRID} strokeOpacity={0.4} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: AXIS }} />
        <YAxis tickFormatter={formatVolume} tick={{ fontSize: 11, fill: AXIS }} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatVolume(v)} />
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
