import { Search, X } from "lucide-react";
import type { ReactNode } from "react";

import { normalize } from "../utils/leagues";

// Wspólne elementy pasków filtrów (Sędziowie, Dyspozycyjność, Mecze, Obiekty).

export function FilterRow({ children, active, onClear, shown, total, noun }: {
  children: ReactNode;
  active: boolean;
  onClear: () => void;
  shown: number;
  total: number;
  noun: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      {children}
      {active && (
        <button className="btn-link" onClick={onClear}>
          <X className="size-3.5" /> Wyczyść filtr
        </button>
      )}
      <span className="text-sm text-zinc-500">{active ? `${shown} z ${total} ${noun}` : `${total} ${noun}`}</span>
    </div>
  );
}

export function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative w-full max-w-sm">
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-zinc-400" />
      <input className="input pl-9" type="search" placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} aria-label={placeholder} />
    </div>
  );
}

export function SelectFilter({ value, onChange, all, options, label }: {
  value: string;
  onChange: (v: string) => void;
  /** Tekst pozycji „bez filtra”, np. „Wszystkie podokręgi”. */
  all: string;
  options: string[];
  label: string;
}) {
  if (options.length === 0) return null;
  return (
    <select className="input w-auto" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
      <option value="">{all}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

/** Każde słowo zapytania musi wystąpić w którymś z pól (bez wielkości liter i polskich znaków). */
export function matchesText(fields: (string | null | undefined)[], query: string): boolean {
  const haystack = normalize(fields.filter(Boolean).join(" "));
  return normalize(query).split(/\s+/).filter(Boolean).every((word) => haystack.includes(word));
}

/** Unikalne wartości posortowane po polsku. */
export function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "pl"));
}

// Kolejność podokręgów jak w backendzie (app/regions.py).
export const REGIONS = ["Warszawa", "Płock", "Radom", "Siedlce", "Ciechanów", "Ostrołęka"];

export function regionOptions(values: string[]): string[] {
  return REGIONS.filter((r) => values.includes(r));
}
