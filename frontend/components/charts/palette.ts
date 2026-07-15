// Brand-neutral, colourblind-aware categorical palette (works in light + dark).
export const PALETTE = [
  "#14b8a6", // teal
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#84cc16", // lime
  "#ec4899", // pink
  "#ef4444", // red
  "#0ea5e9", // sky
  "#a3a3a3", // neutral
];

export const SEMANTIC = {
  retired: "#10b981",
  nonRetired: "#f97316",
  primary: "#0f766e",
  oneTime: "#94a3b8",
  repeat: "#14b8a6",
};

export const SBTI_COLORS: Record<string, string> = {
  "SBTi Aligned": "#10b981",
  "Not SBTi Aligned": "#f43f5e",
  Unknown: "#94a3b8",
};

export const CONFIDENCE_COLORS: Record<string, string> = {
  High: "#10b981",
  Medium: "#f59e0b",
  Low: "#94a3b8",
};

export function colorAt(i: number): string {
  return PALETTE[i % PALETTE.length];
}
