import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { addDays, upcomingSaturday } from "../utils/dates";

// Okres roboczy całej aplikacji: weekend (sobota–niedziela).
interface PeriodState {
  dateFrom: string;
  dateTo: string;
  period: { date_from: string; date_to: string };
  setSaturday: (iso: string) => void;
  shiftWeeks: (weeks: number) => void;
}

const PeriodContext = createContext<PeriodState | null>(null);
const STORAGE_KEY = "obsada.saturday";

function initialSaturday(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  } catch {
    /* localStorage niedostępny */
  }
  return upcomingSaturday();
}

export function PeriodProvider({ children }: { children: ReactNode }) {
  const [saturday, setSaturdayState] = useState(initialSaturday);

  const value = useMemo<PeriodState>(() => {
    const setSaturday = (iso: string) => {
      setSaturdayState(iso);
      try {
        localStorage.setItem(STORAGE_KEY, iso);
      } catch {
        /* ignoruj */
      }
    };
    const dateTo = addDays(saturday, 1);
    return {
      dateFrom: saturday,
      dateTo,
      period: { date_from: saturday, date_to: dateTo },
      setSaturday,
      shiftWeeks: (weeks: number) => setSaturday(addDays(saturday, 7 * weeks)),
    };
  }, [saturday]);

  return <PeriodContext.Provider value={value}>{children}</PeriodContext.Provider>;
}

export function usePeriod(): PeriodState {
  const ctx = useContext(PeriodContext);
  if (!ctx) throw new Error("usePeriod musi być użyty wewnątrz PeriodProvider");
  return ctx;
}
