import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "high" | "medium" | "low" | "aligned" | "unknown" | "danger" | "outline";

const styles: Record<Variant, string> = {
  default: "bg-muted text-muted-foreground",
  high: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300",
  low: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  aligned: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300",
  unknown: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  danger: "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300",
  outline: "border border-border text-foreground",
};

export function Badge({
  variant = "default",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}

export function confidenceVariant(tier: string): Variant {
  const t = tier.toLowerCase();
  if (t === "high") return "high";
  if (t === "medium") return "medium";
  return "low";
}

export function sbtiVariant(alignment: string): Variant {
  if (alignment === "SBTi Aligned") return "aligned";
  if (alignment === "Not SBTi Aligned") return "danger";
  return "unknown";
}
