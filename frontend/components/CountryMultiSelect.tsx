"use client";
import * as React from "react";
import { X } from "lucide-react";
import { Select } from "./ui/input";

// Multi-select of countries: a dropdown adds a country; selected countries show as removable chips.
export function CountryMultiSelect({
  options, value, onChange,
}: { options: string[]; value: string[]; onChange: (v: string[]) => void }) {
  const available = options.filter((o) => !value.includes(o));
  return (
    <div>
      <Select
        value=""
        onChange={(e) => {
          const v = e.target.value;
          if (v && !value.includes(v)) onChange([...value, v]);
          e.currentTarget.value = "";
        }}
      >
        <option value="">{value.length ? "Add another country…" : "All countries"}</option>
        {available.map((o) => <option key={o} value={o}>{o}</option>)}
      </Select>
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {value.map((c) => (
            <span key={c} className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {c}
              <button type="button" onClick={() => onChange(value.filter((x) => x !== c))} aria-label={`Remove ${c}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
