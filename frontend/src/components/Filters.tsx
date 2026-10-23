import { Search, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

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
    <div className="relative w-full max-w-xs">
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
    <select className="input w-auto max-w-56 truncate" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} title={value || all}>
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

const PAGE = 60;

/**
 * Długie tabele (kilkaset sędziów z polami godzin) rysujemy porcjami: najpierw 60 wierszy,
 * kolejne po przewinięciu do końca. Zmiana filtra wraca do pierwszej porcji.
 */
export function useIncremental<T>(items: T[], resetKey: unknown) {
  const [limit, setLimit] = useState(PAGE);
  useEffect(() => setLimit(PAGE), [resetKey]);
  const more = useCallback(() => setLimit((l) => l + PAGE), []);
  return { shown: items.slice(0, limit), hasMore: items.length > limit, more, rest: Math.max(0, items.length - limit) };
}

/** Wiersz na końcu tabeli: po dojechaniu do niego dokłada kolejną porcję. */
export function LoadMoreRow({ colSpan, rest, onMore }: { colSpan: number; rest: number; onMore: () => void }) {
  const ref = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver((entries) => entries[0].isIntersecting && onMore(), { rootMargin: "400px" });
    obs.observe(el);
    return () => obs.disconnect();
  }, [onMore, rest]);
  return (
    <tr ref={ref}>
      <td colSpan={colSpan} className="py-4 text-center">
        <button className="btn-link" onClick={onMore}>
          Pokaż kolejne ({rest})
        </button>
      </td>
    </tr>
  );
}
