export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(n));
}

export function formatVolume(n: number | null | undefined): string {
  if (n === null || n === undefined || n === 0) return "—";
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return formatNumber(n);
}

export function formatPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(1)}%`;
}

export function tCO2e(n: number | null | undefined): string {
  if (n === null || n === undefined || n === 0) return "—";
  return `${formatNumber(n)} tCO₂e`;
}
