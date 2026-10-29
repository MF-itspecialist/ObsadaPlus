import { ArrowRight, CalendarDays, CircleCheck, Gauge, Route, TriangleAlert, UserCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { dayName, formatDate } from "../utils/dates";
import { hhmm } from "../utils/format";

/** Pierścień postępu obsady (procent obsadzonych meczów). */
function CoverageRing({ value, total }: { value: number; total: number }) {
  const pct = total ? value / total : 0;
  const r = 52;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative size-36 shrink-0">
      <svg viewBox="0 0 120 120" className="size-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="currentColor" strokeWidth="10" className="text-white/15" />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className="text-white transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
        <span className="text-3xl font-semibold tabular-nums">{Math.round(pct * 100)}%</span>
        <span className="text-xs text-white/70">obsadzone</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { period } = usePeriod();
  const stats = useAsync(() => api.dashboard(period), [period.date_from]);
  const matches = useAsync(() => api.matches(period), [period.date_from]);
  const s = stats.data;
  const unassigned = (matches.data ?? []).filter((m) => m.status === "UNASSIGNED" || m.status === "PARTIALLY_ASSIGNED");

  return (
    <div>
      <PageHeader title="Dashboard" subtitle={`Dni obsadowe pt–pon: ${formatDate(period.date_from)} – ${formatDate(period.date_to)}`} />
      <ErrorBanner message={stats.error} />
      <ImportChangesBanner />
      {stats.loading && !s && <Loading />}
      {s && (
        <>
          <div className="relative mb-6 overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-brand-600 to-violet-600 p-6 text-white shadow-lift md:p-8">
            <div className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-white/10 blur-2xl" />
            <div className="relative flex flex-col items-start gap-6 md:flex-row md:items-center">
              <CoverageRing value={s.matches_assigned} total={s.matches_total} />
              <div className="flex-1">
                <h2 className="text-xl font-semibold tracking-tight md:text-2xl">
                  {s.matches_total === 0
                    ? "Brak meczów w tym weekendzie"
                    : s.matches_unassigned === 0
                      ? "Wszystkie mecze mają obsadę"
                      : `${s.matches_unassigned} ${s.matches_unassigned === 1 ? "mecz czeka" : "mecze czekają"} na obsadę`}
                </h2>
                <p className="mt-1 max-w-xl text-sm text-white/75">
                  {s.matches_assigned} z {s.matches_total} meczów obsadzonych · {s.total_distance_km.toFixed(0)} km łącznego dojazdu ·{" "}
                  {s.conflicts ? `${s.conflicts} konfliktów do sprawdzenia` : "bez konfliktów"}
                </p>
                <Link
                  to="/assignments"
                  className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-brand-700 shadow-sm transition hover:bg-brand-50"
                >
                  Przejdź do obsady <ArrowRight className="size-4" />
                </Link>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Mecze weekendu" value={s.matches_total} icon={CalendarDays} tone="brand" />
            <StatCard label="Obsadzone" value={s.matches_assigned} icon={CircleCheck} tone="good" />
            <StatCard label="Nieobsadzone" value={s.matches_unassigned} icon={TriangleAlert} tone={s.matches_unassigned ? "bad" : "default"} />
            <StatCard label="Dostępni sędziowie" value={s.available_referees} hint={`aktywnych: ${s.active_referees}`} icon={UserCheck} />
            <StatCard label="Średnia liczba spotkań" value={s.avg_matches_per_referee.toFixed(2)} hint="na aktywnego sędziego" icon={Users} />
            <StatCard label="Łączny dystans" value={`${s.total_distance_km.toFixed(1)} km`} icon={Route} />
            <StatCard label="Średni dystans" value={`${s.avg_distance_km.toFixed(1)} km`} hint="na przypisanie" icon={Gauge} />
            <StatCard label="Konflikty" value={s.conflicts} hint="przypisania łamiące ograniczenia" icon={TriangleAlert} tone={s.conflicts ? "bad" : "default"} />
          </div>
        </>
      )}

      <div className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="font-semibold tracking-tight">Mecze bez pełnej obsady</h2>
          {unassigned.length > 0 && <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">{unassigned.length}</span>}
        </div>
        {matches.loading && <Loading />}
        {!matches.loading && unassigned.length === 0 && <EmptyState title="Wszystko obsadzone" hint="Żaden mecz w tym weekendzie nie czeka na sędziego." />}
        {unassigned.length > 0 && (
          <ul className="divide-y divide-zinc-100 border-t border-zinc-100">
            {unassigned.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center gap-4 px-5 py-3 text-sm">
                <div className="w-28 text-zinc-500">
                  <div className="font-medium text-zinc-900 capitalize">{dayName(m.date)}</div>
                  <div className="tabular-nums">{hhmm(m.start_time)}</div>
                </div>
                <div className="flex-1">
                  <div className="font-medium">
                    {m.home_team} <span className="text-zinc-400">vs</span> {m.away_team}
                  </div>
                  <div className="text-zinc-500">
                    {m.venue.name} · {m.league}
                  </div>
                </div>
                <StatusBadge status={m.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** Ostrzeżenie: import z ostatnich 7 dni zmienił termin lub obiekt obsadzonych meczów. */
function ImportChangesBanner() {
  const runs = useAsync(() => api.importRuns(), []);
  const since = Date.now() - 7 * 24 * 3600 * 1000;
  const changed = new Set((runs.data ?? []).filter((r) => new Date(r.started_at).getTime() >= since).flatMap((r) => r.changes.map((c) => c.match_id)));
  if (!changed.size) return null;
  return (
    <Link to="/imports" className="mb-4 flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 hover:bg-amber-100">
      <TriangleAlert className="size-4 shrink-0" />
      Aktualizacja terminarza zmieniła termin lub obiekt {changed.size} obsadzonych meczów w ostatnim tygodniu. Sprawdź, czy obsada jest dalej aktualna.
      <ArrowRight className="ml-auto size-4 shrink-0" />
    </Link>
  );
}
