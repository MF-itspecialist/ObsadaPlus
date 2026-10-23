import { Car, ChevronDown, ClipboardCheck, FileSpreadsheet, Trophy, Users, Wallet } from "lucide-react";
import { Fragment, useMemo, useState } from "react";

import { EmptyState, ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import { SearchBox, matchesText } from "../components/Filters";
import StatCard from "../components/StatCard";
import { Tag } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { api, type Period } from "../services/api";
import type { RefereeStats } from "../types";
import { formatDate, toIso } from "../utils/dates";

const MONTHS = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"];

const zl = (v: number) => v.toLocaleString("pl-PL", { style: "currency", currency: "PLN" });
const km = (v: number) => `${v.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} km`;

function monthPeriod(year: number, month: number): Period {
  return { date_from: toIso(new Date(year, month, 1)), date_to: toIso(new Date(year, month + 1, 0)) };
}

function seasonPeriod(today: Date): Period {
  const start = today.getMonth() >= 6 ? today.getFullYear() : today.getFullYear() - 1;
  return { date_from: `${start}-07-01`, date_to: `${start + 1}-06-30` };
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

type SortKey = "name" | "matches" | "as_main" | "as_assistant" | "days" | "km" | "amount";

/** Statystyki miesiąca / sezonu i zestawienie kilometrówki (z bieżącej obsady). */
export default function StatisticsPage() {
  const today = new Date();
  const [period, setPeriod] = useState<Period>(monthPeriod(today.getFullYear(), today.getMonth()));
  const stats = useAsync(() => api.statistics(period), [period.date_from, period.date_to]);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "matches", desc: true });
  const [open, setOpen] = useState<number | null>(null);

  const season = seasonPeriod(today);
  const presets: { label: string; p: Period }[] = [
    { label: "Ten miesiąc", p: monthPeriod(today.getFullYear(), today.getMonth()) },
    { label: "Poprzedni miesiąc", p: monthPeriod(today.getFullYear(), today.getMonth() - 1) },
    { label: `Sezon ${season.date_from.slice(0, 4)}/${season.date_to.slice(2, 4)}`, p: season },
  ];

  const rows = useMemo(() => {
    const list = (stats.data?.referees ?? []).filter((r) => matchesText([r.name, r.location], query));
    const dir = sort.desc ? -1 : 1;
    return [...list].sort((a, b) => {
      const x = a[sort.key];
      const y = b[sort.key];
      return (typeof x === "string" ? x.localeCompare(y as string, "pl") : (x as number) - (y as number)) * dir;
    });
  }, [stats.data, query, sort]);

  const s = stats.data?.summary;
  const th = (key: SortKey, label: string, right = true) => (
    <th className={`cursor-pointer select-none ${right ? "text-right" : ""}`} onClick={() => setSort({ key, desc: sort.key === key ? !sort.desc : key !== "name" })}>
      {label}
      {sort.key === key && <span className="ml-1 text-zinc-400">{sort.desc ? "↓" : "↑"}</span>}
    </th>
  );

  return (
    <div>
      <PageHeader title="Statystyki" subtitle="Mecze, obsada i kilometrówka sędziów za miesiąc lub sezon (z zapisanej obsady)">
        <a className="btn-secondary" href={api.mileageXlsxUrl(period)} download>
          <FileSpreadsheet className="size-4" /> Kilometrówka (Excel)
        </a>
      </PageHeader>

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {presets.map(({ label, p }) => {
          const active = p.date_from === period.date_from && p.date_to === period.date_to;
          return (
            <button key={label} className={active ? "btn-primary" : "btn-secondary"} onClick={() => setPeriod(p)}>
              {label}
            </button>
          );
        })}
        <input
          type="month"
          className="input w-auto"
          aria-label="Miesiąc"
          value={period.date_from.slice(0, 7)}
          onChange={(e) => {
            if (!e.target.value) return;
            const [y, m] = e.target.value.split("-").map(Number);
            setPeriod(monthPeriod(y, m - 1));
          }}
        />
        <span className="text-sm text-zinc-500">
          lub od
          <input type="date" className="input mx-2 inline-block w-auto" value={period.date_from} onChange={(e) => e.target.value && setPeriod({ ...period, date_from: e.target.value })} />
          do
          <input type="date" className="input ml-2 inline-block w-auto" value={period.date_to} onChange={(e) => e.target.value && setPeriod({ ...period, date_to: e.target.value })} />
        </span>
      </div>

      <ErrorBanner message={stats.error} />
      {stats.loading && !stats.data ? (
        <Loading />
      ) : !s ? null : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
            <StatCard label="Mecze" value={s.matches} icon={Trophy} tone="brand" hint={`${formatDate(period.date_from)} – ${formatDate(period.date_to)}`} />
            <StatCard
              label="Obsadzone miejsca"
              value={`${s.slots_filled}/${s.slots_total}`}
              icon={ClipboardCheck}
              tone={s.slots_filled === s.slots_total ? "good" : "bad"}
              hint={`${s.matches_fully_assigned} meczów w pełni obsadzonych`}
            />
            <StatCard label="Sędziowie" value={s.referees_used} icon={Users} hint="z co najmniej jednym meczem" />
            <StatCard label="Kilometry" value={km(s.km_total)} icon={Car} hint="dom → mecze → dom" />
            <StatCard label="Kilometrówka" value={zl(s.amount_total)} icon={Wallet} hint={`stawka ${stats.data!.mileage_rate.toLocaleString("pl-PL", { maximumFractionDigits: 4 })} zł/km`} />
          </div>

          {(stats.data!.by_month.length > 1 || stats.data!.by_level.length > 0) && (
            <div className="mb-6 grid gap-4 lg:grid-cols-2">
              {stats.data!.by_month.length > 1 && (
                <div className="card p-5">
                  <h2 className="mb-3 text-sm font-semibold">Miesiące</h2>
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-zinc-100">
                      {stats.data!.by_month.map((m) => (
                        <tr key={m.month}>
                          <td className="py-1.5 capitalize">{monthLabel(m.month)}</td>
                          <td className="py-1.5 text-right tabular-nums">{m.matches} mecz.</td>
                          <td className="py-1.5 text-right tabular-nums text-zinc-500">{km(m.km)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {stats.data!.by_level.length > 0 && (
                <div className="card p-5">
                  <h2 className="mb-3 text-sm font-semibold">Mecze według lig</h2>
                  <div className="space-y-1.5">
                    {stats.data!.by_level.map((l) => (
                      <div key={l.level} className="flex items-center gap-3 text-sm">
                        <span className="w-44 shrink-0 truncate">{l.level}</span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
                          <div className="h-full rounded-full bg-brand-500" style={{ width: `${(l.matches / stats.data!.by_level[0].matches) * 100}%` }} />
                        </div>
                        <span className="w-10 text-right tabular-nums text-zinc-500">{l.matches}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="mb-3 flex flex-wrap items-center gap-3">
            <SearchBox value={query} onChange={setQuery} placeholder="Szukaj sędziego" />
            <span className="text-sm text-zinc-500">{rows.length} sędziów · kliknij wiersz, aby zobaczyć przejazdy</span>
          </div>
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              {rows.length === 0 ? (
                <EmptyState title="Brak przypisań w tym okresie" hint="Statystyki liczą się z zapisanej obsady." />
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      {th("name", "Sędzia", false)}
                      {th("matches", "Mecze")}
                      {th("as_main", "Jako główny")}
                      {th("as_assistant", "Jako asystent")}
                      {th("days", "Dni")}
                      {th("km", "Km")}
                      {th("amount", "Kwota")}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <RefereeRow key={r.referee_id} r={r} open={open === r.referee_id} onToggle={() => setOpen(open === r.referee_id ? null : r.referee_id)} />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function RefereeRow({ r, open, onToggle }: { r: RefereeStats; open: boolean; onToggle: () => void }) {
  return (
    <Fragment>
      <tr className="cursor-pointer" onClick={onToggle}>
        <td>
          <div className="flex items-center gap-2 font-medium">
            <ChevronDown className={`size-4 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />
            {r.name}
          </div>
          <div className="ml-6 text-xs text-zinc-500">{r.location}</div>
        </td>
        <td className="text-right tabular-nums">{r.matches}</td>
        <td className="text-right tabular-nums">{r.as_main}</td>
        <td className="text-right tabular-nums">{r.as_assistant}</td>
        <td className="text-right tabular-nums">{r.days}</td>
        <td className="text-right tabular-nums">{km(r.km)}</td>
        <td className="text-right font-medium tabular-nums">{zl(r.amount)}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} className="bg-zinc-50">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {Object.entries(r.levels).map(([level, n]) => (
                <Tag key={level}>
                  {level}: {n}
                </Tag>
              ))}
            </div>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-zinc-200/60">
                {r.trips.map((t) => (
                  <tr key={t.date}>
                    <td className="py-1.5 pr-4 whitespace-nowrap tabular-nums">{formatDate(t.date)}</td>
                    <td className="py-1.5 pr-4">
                      <div>{t.route}</div>
                      <div className="text-xs text-zinc-500">{t.matches.join(" · ")}</div>
                    </td>
                    <td className="py-1.5 pr-4 text-right whitespace-nowrap tabular-nums">{km(t.km)}</td>
                    <td className="py-1.5 text-right whitespace-nowrap tabular-nums">{zl(t.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </Fragment>
  );
}
