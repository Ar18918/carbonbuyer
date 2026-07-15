// Xynteo brand-led, colourblind-aware categorical palette (works in light + dark).
export const PALETTE = [
  "#0A5AD7", // Xynteo blue
  "#2DAFE6", // Xynteo light blue
  "#00C873", // Xynteo green
  "#FF0064", // Xynteo magenta
  "#0E3A66", // navy tint
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#0ea5e9", // sky
  "#14b8a6", // teal
  "#a3a3a3", // neutral
];

export const SEMANTIC = {
  retired: "#00C873",     // Xynteo green
  nonRetired: "#f97316",  // caution orange
  primary: "#0A5AD7",     // Xynteo blue
  oneTime: "#94a3b8",
  repeat: "#2DAFE6",      // Xynteo light blue
};

export const SBTI_COLORS: Record<string, string> = {
  "SBTi Aligned": "#00C873",
  "Not SBTi Aligned": "#FF0064",
  Unknown: "#94a3b8",
};

export const CONFIDENCE_COLORS: Record<string, string> = {
  High: "#00C873",
  Medium: "#f59e0b",
  Low: "#94a3b8",
};

export function colorAt(i: number): string {
  return PALETTE[i % PALETTE.length];
}
