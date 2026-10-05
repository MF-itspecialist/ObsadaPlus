import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useRef } from "react";

import { usePeriod } from "../context/PeriodContext";
import { formatDate, saturdayOf, upcomingSaturday } from "../utils/dates";

/** Wybór dni obsadowych (piątek–poniedziałek), dla których pracuje cały panel. */
export default function PeriodPicker() {
  const { dateFrom, dateTo, setSaturday, shiftWeeks } = usePeriod();
  const inputRef = useRef<HTMLInputElement>(null);
  const isCurrent = saturdayOf(dateFrom) === upcomingSaturday();

  return (
    <div className="flex items-center gap-2">
      {!isCurrent && (
        <button className="btn-ghost text-xs" onClick={() => setSaturday(upcomingSaturday())}>
          Najbliższy weekend
        </button>
      )}
      <div className="flex items-center rounded-xl bg-white p-1 shadow-soft ring-1 ring-zinc-950/5">
        <button className="icon-btn" onClick={() => shiftWeeks(-1)} aria-label="Poprzednie dni obsadowe">
          <ChevronLeft className="size-4" />
        </button>
        <button
          className="relative flex items-center gap-2 rounded-lg px-3 py-1 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
          onClick={() => inputRef.current?.showPicker?.()}
        >
          <CalendarDays className="size-4 text-brand-600" />
          <span className="hidden text-zinc-500 sm:inline">Pt–Pon</span>
          <span className="tabular-nums">
            {formatDate(dateFrom).slice(0, 5)} – {formatDate(dateTo)}
          </span>
          <input
            ref={inputRef}
            type="date"
            aria-label="Wybierz dni obsadowe"
            className="pointer-events-none absolute inset-0 opacity-0"
            value={saturdayOf(dateFrom)}
            onChange={(e) => e.target.value && setSaturday(saturdayOf(e.target.value))}
          />
        </button>
        <button className="icon-btn" onClick={() => shiftWeeks(1)} aria-label="Następne dni obsadowe">
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  );
}
