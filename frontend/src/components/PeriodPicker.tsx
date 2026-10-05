import { usePeriod } from "../context/PeriodContext";
import { formatDate, saturdayOf } from "../utils/dates";

/** Wybór weekendu (sobota–niedziela), dla którego pracuje cały panel. */
export default function PeriodPicker() {
  const { dateFrom, dateTo, setSaturday, shiftWeeks } = usePeriod();
  return (
    <div className="flex items-center gap-2 text-sm">
      <button className="btn-secondary" onClick={() => shiftWeeks(-1)} aria-label="Poprzedni weekend">
        ‹
      </button>
      <label className="flex items-center gap-2">
        <span className="hidden text-slate-500 sm:inline">Weekend</span>
        <input
          type="date"
          className="input w-40"
          value={dateFrom}
          onChange={(e) => e.target.value && setSaturday(saturdayOf(e.target.value))}
        />
      </label>
      <span className="text-slate-600">
        {formatDate(dateFrom)} – {formatDate(dateTo)}
      </span>
      <button className="btn-secondary" onClick={() => shiftWeeks(1)} aria-label="Następny weekend">
        ›
      </button>
    </div>
  );
}
